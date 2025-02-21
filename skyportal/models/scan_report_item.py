__all__ = ["ScanReportItem"]

import sqlalchemy as sa

from baselayer.app.models import Base


class ScanReportItem(Base):
    """Saved candidate listed in a scan report."""

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the Object associated with the candidate",
    )

    scan_report = sa.Column(
        sa.ForeignKey("scan_report.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the report where the saved candidate is listed",
    )

    saver_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the user that saved this candidate",
    )

    data = sa.Column(
        sa.JSONB,
        nullable=True,
        doc="Source data of the candidate when the report was generated",
    )
