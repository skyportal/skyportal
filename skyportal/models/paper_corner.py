__all__ = ["PaperCornerCache"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from baselayer.app.models import Base

PaperCornerCache = sa.Table(
    "paper_corner_cache",
    Base.metadata,
    sa.Column(
        "obj_id",
        sa.String,
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column("matches", JSONB, nullable=False),
)
