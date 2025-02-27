__all__ = ["ScanReportItem"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import Base


class ScanReportItem(Base):
    """Saved candidate listed in a scan report."""

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the Object associated with the candidate",
    )

    scan_report_id = sa.Column(
        sa.ForeignKey("scanreports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the report where the saved candidate is listed",
    )
    scan_report = relationship("ScanReport", back_populates="items")

    data = sa.Column(
        JSONB,
        nullable=True,
        doc="Source data of the candidate when the report was generated",
    )
