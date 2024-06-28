__all__ = [
    'DefaultObservationPlanRequest',
    'ObservationPlanRequest',
    'ObservationPlanRequestTargetGroup',
    'EventObservationPlan',
    'EventObservationPlanStatistics',
    'PlannedObservation',
]

from astropy import coordinates as ap_coord
from astropy import time as ap_time
from astropy import units as u

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql as psql
from datetime import datetime, timedelta

from baselayer.app.models import (
    Base,
    join_model,
    User,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
    CustomUserAccessControl,
)

from .group import Group
from .followup_request import updatable_by_token_with_listener_acl


class DefaultObservationPlanRequest(Base):
    """A default request for an EventObservationPlan."""

    # TODO: Make read-accessible via target groups
    create = read = AccessibleIfRelatedRowsAreAccessible(allocation="read")
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
        doc="ID of the User who requested the default observation plan request.",
    )

    requester = relationship(
        User,
        back_populates='default_observationplan_requests',
        doc="The User who requested the default requests.",
        foreign_keys=[requester_id],
    )

    payload = sa.Column(
        psql.JSONB,
        nullable=False,
        doc="Content of the default observation plan request.",
    )

    filters = sa.Column(
        psql.JSONB,
        doc="Filters to determine which of the default observation plan requests get executed for which events",
    )

    allocation_id = sa.Column(
        sa.ForeignKey('allocations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    allocation = relationship('Allocation', back_populates='default_observation_plans')

    target_groups = relationship(
        'Group',
        secondary='default_observationplan_groups',
        passive_deletes=True,
        doc='Groups to share the resulting data from this default request with.',
        overlaps='groups',
    )

    default_plan_name = sa.Column(
        sa.String, unique=True, nullable=False, doc='Default plan name'
    )

    auto_send = sa.Column(
        sa.Boolean,
        default=False,
        nullable=True,
        doc="Automatically send to telescope queue?",
    )

    default_survey_efficiencies = relationship(
        'DefaultSurveyEfficiencyRequest',
        back_populates='default_observationplan_request',
        doc='The default survey efficiency requests for this default plan.',
        passive_deletes=True,
    )


DefaultObservationPlanRequestTargetGroup = join_model(
    'default_observationplan_groups',
    DefaultObservationPlanRequest,
    Group,
    new_name='DefaultObservationPlanRequestTargetGroup',
    overlaps='target_groups',
)
DefaultObservationPlanRequestTargetGroup.create = (
    DefaultObservationPlanRequestTargetGroup.update
) = DefaultObservationPlanRequestTargetGroup.delete = (
    AccessibleIfUserMatches('defaultobservationplanrequest.requester')
    & DefaultObservationPlanRequestTargetGroup.read
)


class ObservationPlanRequest(Base):
    """A request for an EventObservationPlan."""

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

    combined_id = sa.Column(
        sa.String,
        nullable=True,
        doc="The unique UUID used to identify combined requests.",
    )

    default_plan = sa.Column(
        sa.Boolean,
        default=False,
        doc="Boolean indicating whether the plan is a default plan.",
    )

    observation_plans = relationship(
        'EventObservationPlan',
        passive_deletes=True,
        doc='Observation plans associated with this request.',
    )

    target_groups = relationship(
        'Group',
        secondary='observationplan_groups',
        passive_deletes=True,
        doc='Groups to share the resulting data from this request with.',
    )

    transactions = relationship(
        'FacilityTransaction',
        back_populates='observation_plan_request',
        passive_deletes=True,
        order_by="FacilityTransaction.created_at.desc()",
    )

    transaction_requests = relationship(
        'FacilityTransactionRequest',
        back_populates='observation_plan_request',
        passive_deletes=True,
        order_by="FacilityTransactionRequest.created_at.desc()",
    )

    @property
    def instrument(self):
        return self.allocation.instrument


ObservationPlanRequestTargetGroup = join_model(
    'observationplan_groups',
    ObservationPlanRequest,
    Group,
    new_name='ObservationPlanRequestTargetGroup',
    overlaps='target_groups',
)
ObservationPlanRequestTargetGroup.create = (
    ObservationPlanRequestTargetGroup.update
) = ObservationPlanRequestTargetGroup.delete = (
    AccessibleIfUserMatches('observationplanrequest.requester')
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
        overlaps='observation_plans',
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
        overlaps='plans',
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc='GCN Event timestamp that this observation plan belongs to',
    )

    plan_name = sa.Column(sa.String, unique=True, doc='Plan name')

    validity_window_start = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc='Start of validity window',
    )

    validity_window_end = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.now() + timedelta(1),
        doc='End of validity window',
    )

    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending submission",
        index=True,
        doc="The status of the observing plan.",
    )

    planned_observations = relationship(
        "PlannedObservation",
        passive_deletes=True,
        doc='Planned observations associated with this plan.',
    )

    survey_efficiency_analyses = relationship(
        'SurveyEfficiencyForObservationPlan',
        cascade='delete',
        passive_deletes=True,
        doc="Survey efficiency analyses of the event.",
        overlaps='observation_plan',
    )

    statistics = relationship(
        "EventObservationPlanStatistics",
        passive_deletes=True,
        doc='Observation statistics associated with this plan.',
    )


class EventObservationPlanStatistics(Base):
    """Statistics derived from an EventObservationPlan.
    Tile information, including the event time, localization ID, field IDs,
    tiling name, and tile probabilities."""

    __tablename__ = 'event_observation_plan_statistics'

    observation_plan_id = sa.Column(
        sa.ForeignKey('eventobservationplans.id', ondelete="CASCADE"),
        nullable=False,
        doc='Event observation plan ID',
    )

    observation_plan = relationship(
        "EventObservationPlan",
        foreign_keys=observation_plan_id,
        doc="The EventObservationPlan that this planned observation belongs to",
        overlaps='statistics',
    )

    localization_id = sa.Column(
        sa.ForeignKey('localizations.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    statistics = sa.Column(
        psql.JSONB,
        nullable=False,
        doc="Statistics related to the observation plan (sky area, 2D probability, etc.).",
    )


class PlannedObservation(Base):
    """A single planned exposure as part of an EventObservationPlan.
    Tile information, including the event time, localization ID, field IDs,
    tiling name, and tile probabilities."""

    observation_plan_id = sa.Column(
        sa.ForeignKey('eventobservationplans.id', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc='Event observation plan ID',
    )

    observation_plan = relationship(
        "EventObservationPlan",
        foreign_keys=observation_plan_id,
        doc="The EventObservationPlan that this planned observation belongs to",
        overlaps='planned_observations',
    )

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    instrument = relationship("Instrument")

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc='GCN Event timestamp that this observation plan belongs to',
    )

    field_id = sa.Column(
        sa.ForeignKey("instrumentfields.id", ondelete="CASCADE"),
        index=True,
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

    def rise_time(self, altitude=30 * u.degree):
        """The rise time of the field as an astropy.time.Time."""
        observer = self.instrument.telescope.observer
        if observer is None:
            return None

        sunset = self.instrument.telescope.next_sunset(ap_time.Time.now()).reshape((1,))
        sunrise = self.instrument.telescope.next_sunrise(ap_time.Time.now()).reshape(
            (1,)
        )

        coord = ap_coord.SkyCoord(self.field.ra, self.field.dec, unit='deg')

        next_rise = observer.target_rise_time(
            sunset, coord, which='next', horizon=altitude
        )

        # if next rise time is after next sunrise, the target rises before
        # sunset. show the previous rise so that the target is shown to be
        # "already up" when the run begins (a beginning of night target).

        recalc = next_rise > sunrise
        if recalc.any():
            next_rise = observer.target_rise_time(
                sunset, coord, which='previous', horizon=altitude
            )

        return next_rise

    def set_time(self, altitude=30 * u.degree):
        """The set time of the field as an astropy.time.Time."""
        observer = self.instrument.telescope.observer
        if observer is None:
            return None

        sunset = self.instrument.telescope.next_sunset(ap_time.Time.now())
        coord = ap_coord.SkyCoord(self.field.ra, self.field.dec, unit='deg')
        return observer.target_set_time(sunset, coord, which='next', horizon=altitude)
