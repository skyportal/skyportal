__all__ = ['Allocation']

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy_utils.types.encrypted.encrypted_type import EncryptedType, AesEngine
from sqlalchemy_utils.types import JSONType

import json

from baselayer.app.env import load_env
from baselayer.app.models import Base, AccessibleIfRelatedRowsAreAccessible
from .group import accessible_by_group_members


_, cfg = load_env()


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
    requests = relationship(
        'FollowupRequest',
        back_populates='allocation',
        doc='The requests made against this allocation.',
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

    @property
    def altdata(self):
        if self._altdata is None:
            return {}
        else:
            return json.loads(self._altdata)

    @altdata.setter
    def altdata(self, value):
        self._altdata = value
