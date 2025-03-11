__all__ = ["ScanReport"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import Base


class ScanReport(Base):
    """A report listing saved candidates during a scan session between two dates."""

    author_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        doc="ID of the user that created this report",
    )
    author = relationship("User", doc="The User that created this report")

    items = relationship(
        "ScanReportItem",
        back_populates="scan_report",
        cascade="delete, delete-orphan",
        passive_deletes=True,
        doc="List of candidates saved in this scanning report",
    )

    groups = relationship(
        "Group",
        secondary="group_scan_reports",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="The groups that have access to this report",
    )

    options = sa.Column(
        JSONB,
        nullable=False,
        doc="Options used to create this report",
    )
