# this is the model of a table that has: a source id, a localization id, a flag to indicate if the source is confirmed or rejected

__all__ = ['SourcesInGCN']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
)
from baselayer.app.env import load_env

from .group import accessible_by_group_members

_, cfg = load_env()


class SourcesInGCN(Base):

    create = read = accessible_by_group_members
    update = delete = accessible_by_group_members

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc='ID of the Obj.',
    )

    obj = relationship(
        'Obj',
        back_populates='sources_in_gcns',
        doc='The assigned Obj.',
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc='UTC event timestamp',
    )

    confirmed_or_rejected = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Confirmed",
    )
