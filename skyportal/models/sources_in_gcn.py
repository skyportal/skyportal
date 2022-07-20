# this is the model of a table that has: a source id, a localization id, a flag to indicate if the source is confirmed or rejected

__all__ = ['SourcesInGCN']

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from traitlets import default


from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    UserAccessControl,
    DBSession,
    safe_aliased,
)
from baselayer.app.env import load_env
from skyportal.models.source import Source
from skyportal.models.localization import Localization

from .group import GroupUser, accessible_by_group_members

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

    localization_id = sa.Column(
        sa.ForeignKey("localizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Localization ID",
    )

    localization = relationship(
        "Localization",
        foreign_keys=[localization_id],
        back_populates="sources_in_gcns",
        doc="Localization"
    )

    confirmed = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Confirmed",
    )

    rejected = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Rejected",
    )

    # it can be either confirmed or rejected, not both True at the same time
    def confirm(self):
        self.confirmed = True
        self.rejected = False

    def reject(self):
        self.confirmed = False
        self.rejected = True





