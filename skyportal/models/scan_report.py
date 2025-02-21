__all__ = ["ScanReport"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base


class ScanReport(Base):
    """A report listing saved candidates during a scan session between two dates."""

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the user that generated this report",
    )

    items = relationship(
        "ScanReportItem",
        backref="scan_report",
        cascade="delete, delete-orphan",
        passive_deletes=True,
        doc="List of candidates saved in this scan report",
    )
