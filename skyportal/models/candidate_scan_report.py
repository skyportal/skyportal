__all__ = ["CandidateScanReport"]

import sqlalchemy as sa

from baselayer.app.models import Base


class CandidateScanReport(Base):
    """Candidate saved to the scan report model."""

    date = sa.Column(
        sa.DateTime,
        nullable=False,
        doc="ISO UTC time when the candidate was saved to the report",
    )

    scanner = sa.Column(sa.String, nullable=False, doc="Scanner name")

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the Obj",
    )

    comment = sa.Column(sa.String, nullable=True, doc="Comment")

    already_classified = sa.Column(
        sa.Boolean, nullable=True, doc="Is already classified"
    )

    host_redshift = sa.Column(sa.Float, nullable=True, doc="Host redshift")

    current_mag = sa.Column(sa.Float, nullable=True, doc="Current mag")

    current_age = sa.Column(sa.Float, nullable=True, doc="Current age")

    forced_photometry_requested = sa.Column(
        sa.Boolean, nullable=True, doc="Forced photometry requested"
    )

    saver_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the user that saved this candidate to the report",
    )
