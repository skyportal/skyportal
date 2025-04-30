import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base, join_model
from skyportal.models import User
from skyportal.models.obj import Obj


class ObjTagOption(Base):
    """A record of a list of tags that are available."""

    name = sa.Column(sa.String, nullable=False, doc="Tags list.", unique=True)


ObjTag = join_model("obj_tag", ObjTagOption, Obj)

read = update = delete = AccessibleIfUserMatches("user")

ObjTag.author_id = sa.Column(
    "author_id",
    sa.ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
    doc="ID of the user who created the tag association",
)

ObjTag.author = relationship(
    User,
    doc="The associated User",
    foreign_keys=[ObjTag.author_id],
)

ObjTag.__table_args__ = (sa.Index("obj_tags", "name", "tag_id", unique=True),)
