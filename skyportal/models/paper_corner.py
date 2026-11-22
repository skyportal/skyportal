__all__ = ["PaperCornerCache", "tns_paper_sources"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from baselayer.app.models import Base

from .group import Group
from .obj import Obj
from .source import Source

PaperCornerCache = sa.Table(
    "paper_corner_cache",
    Base.metadata,
    sa.Column(
        "obj_id",
        sa.String,
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column("tns_name", sa.String, nullable=False),
    sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("matches", JSONB, nullable=False),
)


def tns_paper_sources(stmt, public_group_name):
    # TNS ingestion saves the unprefixed designation as the source ID.
    designation = sa.func.substring(
        sa.func.lower(Obj.tns_name), r"^[a-z]+[[:space:]]*([0-9]+[a-z]+)$"
    )
    public_group_id = (
        sa.select(Group.id).where(Group.name == public_group_name).scalar_subquery()
    )
    return stmt.join(Obj, Obj.id == Source.obj_id).where(
        Source.group_id == public_group_id,
        Source.active.is_(True),
        Obj.tns_info["name_prefix"].astext.is_not(None),
        sa.func.lower(Obj.id) == designation,
    )
