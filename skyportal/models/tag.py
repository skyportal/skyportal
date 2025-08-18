import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, CustomUserAccessControl, join_model
from skyportal.models import User
from skyportal.models.obj import Obj


def objtag_access_logic(cls, user_or_token):
    query = sa.select(cls)

    if (
        not user_or_token.is_system_admin
        or "Manage sources" not in user_or_token.permissions
    ):
        query = query.where(cls.author_id == user_or_token.id)
    return query


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


ObjTag.create = ObjTag.read
ObjTag.update = ObjTag.delete = CustomUserAccessControl(objtag_access_logic)
