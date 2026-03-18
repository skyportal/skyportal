import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, CustomUserAccessControl, join_model
from skyportal.models import User
from skyportal.models.group import (
    Group,
    accessible_by_group_members,
    accessible_by_groups_members,
)
from skyportal.models.obj import Obj


def objtag_access_logic(cls, user_or_token):
    """Access logic for updating/deleting ObjTags.

    - System admins: can update/delete any tag
    - Users with "Manage sources": can update/delete tags in their groups
    - Regular users: can only update/delete tags they authored
    """
    query = sa.select(cls)

    if user_or_token.is_system_admin:
        return query

    if "Manage sources" in user_or_token.permissions:
        return query

    return query.where(cls.author_id == user_or_token.id)


class ObjTagOption(Base):
    """Store available tags that can be associated to an object."""

    name = sa.Column(
        sa.String,
        nullable=False,
        doc="Available tags that can be associated to an object.",
        unique=True,
    )

    color = sa.Column(
        sa.String,
        nullable=True,
        default=None,
        doc="Hex color code for the tag display (e.g., #3a87ad)",
    )


ObjTag = join_model("obj_tags", Obj, ObjTagOption)

ObjTag.author_id = sa.Column(
    "author_id",
    sa.ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    doc="ID of the user who created the tag association",
)

ObjTag.author = relationship(User, doc="The associated User")

GroupObjTag = join_model("group_obj_tags", Group, ObjTag)
GroupObjTag.__doc__ = "Join table mapping Groups to ObjTags."
GroupObjTag.create = accessible_by_group_members
GroupObjTag.delete = GroupObjTag.update = accessible_by_group_members

ObjTag.groups = relationship(
    "Group",
    secondary="group_obj_tags",
    back_populates="obj_tags",
    cascade="save-update, merge, refresh-expire, expunge",
    passive_deletes=True,
    doc="Groups that can access this object tag.",
)

Group.obj_tags = relationship(
    ObjTag,
    secondary="group_obj_tags",
    back_populates="groups",
    cascade="save-update, merge, refresh-expire, expunge",
    passive_deletes=True,
    doc="Object tags associated with this group.",
)

ObjTag.create = ObjTag.read = accessible_by_groups_members
ObjTag.update = ObjTag.delete = accessible_by_groups_members & CustomUserAccessControl(
    objtag_access_logic
)


def serialize_obj_tag(tag, user_group_ids):
    """Serialize an ObjTag, filtering groups to only those the user can see.

    Parameters
    ----------
    tag : ObjTag
    user_group_ids : set or None
        Set of group IDs the user belongs to. None means system admin (all groups visible).
    """
    return {
        **tag.to_dict(),
        "name": tag.objtagoption.name,
        "groups": [
            g.to_dict()
            for g in tag.groups
            if user_group_ids is None or g.id in user_group_ids
        ],
    }
