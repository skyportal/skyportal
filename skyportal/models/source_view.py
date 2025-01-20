__all__ = ["SourceView"]

from datetime import datetime

import sqlalchemy as sa

from baselayer.app.models import Base


class SourceView(Base):
    """Record of an instance in which a Source was viewed via the frontend or
    retrieved via the API (for use in the "Top Sources" widget).
    """

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        unique=False,
        index=True,
        doc="Object ID for which the view was registered.",
    )
    username_or_token_id = sa.Column(
        sa.String,
        nullable=False,
        unique=False,
        doc="Username or token ID of the viewer.",
    )
    is_token = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether the viewer was a User or a Token.",
    )
    created_at = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="UTC timestamp of the view.",
    )
