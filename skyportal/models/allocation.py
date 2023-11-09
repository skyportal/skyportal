__all__ = ['Allocation', 'AllocationUser']

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy_utils.types.encrypted.encrypted_type import EncryptedType, AesEngine
from sqlalchemy_utils.types import JSONType
from sqlalchemy.dialects.postgresql import ARRAY as pg_array

import json

from baselayer.app.env import load_env
from baselayer.app.models import (
    Base,
    User,
    AccessibleIfRelatedRowsAreAccessible,
    join_model,
    UserAccessControl,
    CustomUserAccessControl,
    DBSession,
    safe_aliased,
)
from .group import GroupUser, accessible_by_group_members
from ..enum_types import allowed_allocation_types, ALLOWED_ALLOCATION_TYPES


_, cfg = load_env()


def allocationuser_access_logic(cls, user_or_token):
    aliased = safe_aliased(cls)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    user_allocation_admin = (
        DBSession()
        .query(Allocation)
        .join(GroupUser, GroupUser.group_id == Allocation.group_id)
        .filter(sa.and_(GroupUser.user_id == user_id, GroupUser.admin.is_(True)))
    )
    query = (
        DBSession().query(cls).join(aliased, cls.allocation_id == aliased.allocation_id)
    )
    if not user_or_token.is_system_admin:
        query = query.filter(
            sa.or_(
                aliased.user_id == user_id,
                sa.and_(aliased.admin.is_(True), aliased.user_id == user_id),
                aliased.allocation_id.in_(
                    [allocation.id for allocation in user_allocation_admin.all()]
                ),
            )
        )
    return query


class Allocation(Base):
    """An allocation of observing time on a robotic instrument."""

    create = (
        read
    ) = (
        update
    ) = delete = accessible_by_group_members & AccessibleIfRelatedRowsAreAccessible(
        instrument='read'
    )

    pi = sa.Column(sa.String, doc="The PI of the allocation's proposal.")
    proposal_id = sa.Column(
        sa.String, doc="The ID of the proposal associated with this allocation."
    )
    start_date = sa.Column(sa.DateTime, doc='The UTC start date of the allocation.')
    end_date = sa.Column(sa.DateTime, doc='The UTC end date of the allocation.')
    hours_allocated = sa.Column(
        sa.Float, nullable=False, doc='The number of hours allocated.'
    )
    default_share_group_ids = sa.Column(
        sa.ARRAY(sa.Integer), comment='List of default group IDs to share data with'
    )
    types = sa.Column(
        pg_array(allowed_allocation_types),
        nullable=False,
        # the default should be an array with just "triggered" in it
        server_default=sa.text("'{" + ALLOWED_ALLOCATION_TYPES[0] + "}'"),
        doc='The type of allocation.',
    )

    requests = relationship(
        'FollowupRequest',
        back_populates='allocation',
        doc='The requests made against this allocation.',
        passive_deletes=True,
    )
    default_requests = relationship(
        'DefaultFollowupRequest',
        back_populates='allocation',
        doc='The default requests made against this allocation.',
        passive_deletes=True,
    )
    default_observation_plans = relationship(
        'DefaultObservationPlanRequest',
        back_populates='allocation',
        doc='The default observing plan requests for this allocation.',
        passive_deletes=True,
    )
    catalog_queries = relationship(
        'CatalogQuery',
        back_populates='allocation',
        doc='The catalog queries for this allocation.',
        passive_deletes=True,
    )
    observation_plans = relationship(
        'ObservationPlanRequest',
        back_populates='allocation',
        doc='The observing plan requests for this allocation.',
        passive_deletes=True,
    )
    group_id = sa.Column(
        sa.ForeignKey('groups.id', ondelete='CASCADE'),
        index=True,
        doc='The ID of the Group the allocation is associated with.',
        nullable=False,
    )
    group = relationship(
        'Group',
        back_populates='allocations',
        doc='The Group the allocation is associated with.',
    )

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        index=True,
        doc="The ID of the Instrument the allocation is associated with.",
        nullable=False,
    )
    instrument = relationship(
        'Instrument',
        back_populates='allocations',
        doc="The Instrument the allocation is associated with.",
    )

    _altdata = sa.Column(
        EncryptedType(JSONType, cfg['app.secret_key'], AesEngine, 'pkcs5')
    )

    allocation_users = relationship(
        'AllocationUser',
        back_populates='allocation',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc='Elements of a join table mapping Users to Allocations.',
        overlaps='allocations, users',
    )

    gcn_triggers = relationship(
        'GcnTrigger',
        back_populates='allocation',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc='Elements of a join table mapping GCNs to Allocations with a trigger status.',
        overlaps='allocations, gcnevents',
    )

    @property
    def altdata(self):
        if self._altdata is None:
            return {}
        else:
            return json.loads(self._altdata)

    @altdata.setter
    def altdata(self, value):
        self._altdata = value


AllocationUser = join_model('allocation_users', Allocation, User)
AllocationUser.__doc__ = "Join table mapping `Allocation`s to `User`s."
AllocationUser.create = AllocationUser.read
AllocationUser.update = AllocationUser.delete = CustomUserAccessControl(
    allocationuser_access_logic
)
