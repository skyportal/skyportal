__all__ = ['Source']

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy import func

from baselayer.app.models import (
    ThreadSession,
    join_model,
    UserAccessControl,
    CustomUserAccessControl,
)

from .obj import Obj
from .group import Group, GroupUser, accessible_by_group_members


Source = join_model("sources", Group, Obj)

# This relationship is defined here to prevent a circular import.
# Please see obj.py for other Obj relationships.
Obj.sources = relationship(
    Source,
    back_populates='obj',
    cascade='delete',
    passive_deletes=True,
    doc="Instances in which a group saved this Obj.",
)


def source_create_access_logic(cls, user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = ThreadSession().query(cls)
    if not user_or_token.is_system_admin:
        query = query.join(Group).join(GroupUser)
        query = query.filter(GroupUser.user_id == user_id, GroupUser.can_save.is_(True))
    return query


Source.create = CustomUserAccessControl(source_create_access_logic)
Source.read = Source.update = Source.delete = accessible_by_group_members

Source.__doc__ = (
    "An Obj that has been saved to a Group. Once an Obj is saved as a Source, "
    "the Obj is shielded in perpetuity from automatic database removal. "
    "If a Source is 'unsaved', its 'active' flag is set to False, but "
    "it is not purged."
)

Source.saved_by_id = sa.Column(
    sa.ForeignKey("users.id"),
    nullable=True,
    unique=False,
    index=True,
    doc="ID of the User that saved the Obj to its Group.",
)
Source.saved_by = relationship(
    "User",
    foreign_keys=[Source.saved_by_id],
    backref="saved_sources",
    doc="User that saved the Obj to its Group.",
)
utcnow = func.timezone('UTC', func.current_timestamp())
Source.saved_at = sa.Column(
    sa.DateTime,
    nullable=False,
    default=utcnow,
    index=True,
    doc="ISO UTC time when the Obj was saved to its Group.",
)
Source.active = sa.Column(
    sa.Boolean,
    server_default="true",
    doc="Whether the Obj is still 'active' as a Source in its Group. "
    "If this flag is set to False, the Source will not appear in the Group's "
    "sample.",
)
Source.requested = sa.Column(
    sa.Boolean,
    server_default="false",
    doc="True if the source has been shared with another Group, but not saved "
    "by the recipient Group.",
)

Source.unsaved_by_id = sa.Column(
    sa.ForeignKey("users.id"),
    nullable=True,
    unique=False,
    index=True,
    doc="ID of the User who unsaved the Source.",
)
Source.unsaved_by = relationship(
    "User", foreign_keys=[Source.unsaved_by_id], doc="User who unsaved the Source."
)
Source.unsaved_at = sa.Column(
    sa.DateTime,
    nullable=True,
    doc="ISO UTC time when the Obj was unsaved from Group.",
)
