import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base, join_model
from skyportal.models import User
from skyportal.models.obj import Obj


class ObjTagOption(Base):
    """A record of a list of tags that are available."""

    tag_name = sa.Column(sa.String, nullable=False, doc="Tags list.", unique=True)


ObjTags = join_model("obj_tags", ObjTagOption, Obj)

read = update = delete = AccessibleIfUserMatches("user")

ObjTags.user_id = sa.Column(
    "user_id",
    sa.ForeignKey("users.id", ondelete="SET NULL"),
    nullable=False,
    index=True,
    doc="ID of the user who created the tag association",
)

ObjTags.user = relationship(
    User,
    doc="The associated User",
    foreign_keys=[ObjTags.user_id],
)

ObjTags.__table_args__ = (sa.Index("obj_tags", "tag_name", "tag_id", unique=True),)
