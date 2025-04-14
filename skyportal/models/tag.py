import conesearch_alchemy as ca
import sqlalchemy as sa

from baselayer.app.models import (
    Base,
    join_model,
)
from skyportal.models.source import Source


class ObjTagOption(Base):
    """A record of a list of tags that are available."""

    tag_name = sa.Column(sa.String, nullable=False, doc="Tags list.", unique=True)


ObjTags = join_model("obj_tags", ObjTagOption, Source)
ObjTags.__table_args__ = (sa.Index("obj_tags", "tag_name", "tag_id", unique=True),)
