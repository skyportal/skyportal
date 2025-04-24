import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, join_model
from skyportal.models import User
from skyportal.models.obj import Obj


class ObjTagOption(Base):
    """Store available tags that can be associated to an object."""

    name = sa.Column(
        sa.String,
        nullable=False,
        doc="Available tags that can be associated to an object.",
        unique=True,
    )


ObjTag = join_model("obj_tag", ObjTagOption, Obj)

ObjTag.author_id = sa.Column(
    "author_id",
    sa.ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
    doc="ID of the user who created the tag association",
)

ObjTag.author = relationship(User, doc="The associated User")
