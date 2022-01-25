__all__ = ['ObservationPlanRequest', 'ObservationPlanRequestTargetGroup']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from sqlalchemy.dialects import postgresql as psql

from baselayer.app.models import (
    Base,
    DBSession,
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
