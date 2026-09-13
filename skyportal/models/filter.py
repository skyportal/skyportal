__all__ = ["Filter"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfRelatedRowsAreAccessible, Base

from .group import accessible_by_group_members


class Filter(Base):
    """An alert filter that operates on a Stream. A Filter is associated
    with exactly one Group, and a Group may have multiple operational Filters.
    """

    # TODO: Track filter ownership and allow owners to update, delete filters
    create = read = update = delete = (
        accessible_by_group_members
        & AccessibleIfRelatedRowsAreAccessible(stream="read")
    )

    name = sa.Column(sa.String, nullable=False, unique=False, doc="Filter name.")
    stream_id = sa.Column(
        sa.ForeignKey("streams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Filter's Stream.",
    )
    altdata = sa.Column(
        JSONB,
        nullable=True,
        doc="Arbitrary additional JSON data associated with the Filter.",
    )
    stream = relationship(
        "Stream",
        foreign_keys=[stream_id],
        back_populates="filters",
        doc="The Filter's Stream.",
    )
    group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Filter's Group.",
    )
    group = relationship(
        "Group",
        foreign_keys=[group_id],
        back_populates="filters",
        doc="The Filter's Group.",
    )
    broker_id = sa.Column(
        sa.ForeignKey("brokers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the Broker this Filter runs on, if any.",
    )
    broker = relationship(
        "Broker",
        foreign_keys=[broker_id],
        back_populates="filters",
        doc="The Broker this Filter runs on.",
    )
    autosave = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="If set, objects passing this filter during broker ingestion are "
        "auto-saved as Sources to the Filter's Group (in addition to being "
        "registered as Candidates).",
    )
    candidates = relationship(
        "Candidate",
        back_populates="filter",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        order_by="Candidate.passed_at",
        doc="Candidates that have passed the filter.",
    )
