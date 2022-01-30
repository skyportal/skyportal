__all__ = [
    'ObservationPlanRequest',
    'ObservationPlanRequestTargetGroup',
    'EventObservationPlan',
    'PlannedObservation',
]

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timedelta
import healpy as hp
import numpy as np

from baselayer.app.models import (
    Base,
    DBSession,
    Localization,
    join_model,
    User,
    public,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
    CustomUserAccessControl,
)

from .group import Group
from .instrument import Instrument
from .allocation import Allocation


def updatable_by_token_with_listener_acl(cls, user_or_token):
    if user_or_token.is_admin:
        return public.query_accessible_rows(cls, user_or_token)

    instruments_with_apis = (
        Instrument.query_records_accessible_by(user_or_token)
        .filter(Instrument.listener_classname.isnot(None))
        .all()
    )

    api_map = {
        instrument.id: instrument.listener_class.get_acl_id()
        for instrument in instruments_with_apis
    }

    accessible_instrument_ids = [
        instrument_id
        for instrument_id, acl_id in api_map.items()
        if acl_id in user_or_token.permissions
    ]

    return (
        DBSession()
        .query(cls)
        .join(Allocation)
        .join(Instrument)
        .filter(Instrument.id.in_(accessible_instrument_ids))
    )


class ObservationPlanRequest(Base):
    """A request for an observation plan."""

    # TODO: Make read-accessible via target groups
    create = read = AccessibleIfRelatedRowsAreAccessible(
        gcnevent="read", allocation="read"
    )
    update = delete = (
        (
            AccessibleIfUserMatches('allocation.group.users')
            | AccessibleIfUserMatches('requester')
        )
        & read
    ) | CustomUserAccessControl(updatable_by_token_with_listener_acl)

    requester_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        doc="ID of the User who requested the follow-up.",
    )

    requester = relationship(
        User,
        back_populates='observationplan_requests',
        doc="The User who requested the follow-up.",
        foreign_keys=[requester_id],
    )

    last_modified_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        doc="The ID of the User who last modified the request.",
    )

    last_modified_by = relationship(
        User,
        doc="The user who last modified the request.",
        foreign_keys=[last_modified_by_id],
    )

    gcnevent = relationship(
        'GcnEvent',
        back_populates='observationplan_requests',
        doc="The target GcnEvent.",
    )
    gcnevent_id = sa.Column(
        sa.ForeignKey('gcnevents.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the target GcnEvent.",
    )

    localization = relationship(
        'Localization',
        back_populates='observationplan_requests',
        doc="The target Localization.",
    )
    localization_id = sa.Column(
        sa.ForeignKey('localizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the target Localization.",
    )

    payload = sa.Column(
        psql.JSONB, nullable=False, doc="Content of the observation plan request."
    )

    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending submission",
        index=True,
        doc="The status of the request.",
    )

    allocation_id = sa.Column(
        sa.ForeignKey('allocations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    allocation = relationship('Allocation', back_populates='observation_plans')

    target_groups = relationship(
        'Group',
        secondary='observationplan_groups',
        passive_deletes=True,
        doc='Groups to share the resulting data from this request with.',
    )

    @property
    def instrument(self):
        return self.allocation.instrument


ObservationPlanRequestTargetGroup = join_model(
    'observationplan_groups', ObservationPlanRequest, Group
)
ObservationPlanRequestTargetGroup.create = (
    ObservationPlanRequestTargetGroup.update
) = ObservationPlanRequestTargetGroup.delete = (
    AccessibleIfUserMatches('followuprequest.requester')
    & ObservationPlanRequestTargetGroup.read
)


class EventObservationPlan(Base):
    """Tiling information, including the event time, localization ID, tile IDs,
    and plan name"""

    observation_plan_request_id = sa.Column(
        sa.ForeignKey('observationplanrequests.id', ondelete="CASCADE"),
        nullable=False,
        doc='ObservationPlanRequest ID',
    )

    observation_plan_request = relationship(
        "ObservationPlanRequest",
        foreign_keys=observation_plan_request_id,
        doc="The request that this observation plan belongs to",
    )

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    instrument = relationship(
        "Instrument",
        foreign_keys=instrument_id,
        doc="The Instrument that this observation plan belongs to",
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc='UTC event timestamp',
    )

    plan_name = sa.Column(sa.String, unique=True, doc='Plan name')

    validity_window_start = sa.Column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now(),
        doc='Start of validity window',
    )

    validity_window_end = sa.Column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now() + timedelta(1),
        doc='End of validity window',
    )

    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending submission",
        index=True,
        doc="The status of the observing plan.",
    )

    planned_observations = relationship("PlannedObservation")

    @property
    def start_observation(self):
        """Time of the first planned observation."""
        if self.planned_observations:
            return min(
                [
                    planned_observation.obstime
                    for planned_observation in self.planned_observations
                ]
            )
        else:
            return None

    @hybrid_property
    def num_observations(self):
        """Number of planned observation."""
        return len(self.planned_observations)

    @num_observations.expression
    def num_observations(cls):
        """Number of planned observation."""
        return cls.planned_observations.count()

    @property
    def total_time(self):
        """Total observation time (seconds)."""
        return sum(_.exposure_time for _ in self.planned_observations)

    @property
    def tot_time_with_overheads(self):
        overhead = sum(_.overhead_per_exposure for _ in self.planned_observations)
        return overhead + self.total_time

    @property
    def ipix(self):
        return {
            i
            for planned_observation in self.planned_observations
            if planned_observation.field.ipix is not None
            for i in planned_observation.field.ipix
        }

    @property
    def area(self):
        nside = Localization.nside
        return hp.nside2pixarea(nside, degrees=True) * len(self.ipix)

    def get_probability(self, localization):
        ipix = np.asarray(list(self.ipix))
        return localization.flat_2d[ipix].sum()


class PlannedObservation(Base):
    """Tile information, including the event time, localization ID, field IDs,
    tiling name, and tile probabilities."""

    observation_plan_id = sa.Column(
        sa.ForeignKey('eventobservationplans.id', ondelete="CASCADE"),
        nullable=False,
        doc='Event observation plan ID',
    )

    observation_plan = relationship(
        "EventObservationPlan",
        foreign_keys=observation_plan_id,
        doc="The EventObservationPlan that this planned observation belongs to",
    )

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc='UTC event timestamp',
    )

    field_id = sa.Column(
        sa.ForeignKey("instrumentfields.id", ondelete="CASCADE"),
        primary_key=True,
        doc='Field ID',
    )

    field = relationship("InstrumentField")

    exposure_time = sa.Column(
        sa.Integer, nullable=False, doc='Exposure time in seconds'
    )

    weight = sa.Column(
        sa.Float, nullable=False, doc='Weight associated with each observation'
    )

    filt = sa.Column(sa.String, nullable=False, doc='Filter')

    obstime = sa.Column(sa.DateTime, nullable=False, doc='UTC observation timestamp')

    overhead_per_exposure = sa.Column(
        sa.Integer, nullable=False, doc='Overhead time per exposure in seconds'
    )

    planned_observation_id = sa.Column(
        sa.Integer, nullable=False, doc='Observation number'
    )
