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

    photometry_followup = sa.Column(
        sa.Boolean, nullable=True, doc="Assigned for photometry followup"
    )

    photometry_assigned_to = sa.Column(
        sa.String, nullable=True, doc="Photometry followup assigned to"
    )

    is_real = sa.Column(
        sa.Boolean, nullable=True, doc="Sure if this is a real transient"
    )

    spectroscopy_requested = sa.Column(
        sa.Boolean, nullable=True, doc="Spectroscopy requested"
    )

    spectroscopy_assigned_to = sa.Column(
        sa.String, nullable=True, doc="Spectroscopy followup assigned to"
    )

    priority = sa.Column(sa.Integer, nullable=True, doc="Priority for")

    saver_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the user that saved this candidate to the report",
    )
