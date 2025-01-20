__all__ = ["ClassicalAssignment"]

import sqlalchemy as sa
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfRelatedRowsAreAccessible, Base

from ..enum_types import followup_priorities


class ClassicalAssignment(Base):
    """Assignment of an Obj to an Observing Run as a target."""

    create = read = update = delete = AccessibleIfRelatedRowsAreAccessible(
        obj="read", run="read"
    )

    requester_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The ID of the User who created this assignment.",
    )
    requester = relationship(
        "User",
        back_populates="assignments",
        foreign_keys=[requester_id],
        doc="The User who created this assignment.",
    )

    last_modified_by_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_id])

    obj = relationship("Obj", back_populates="assignments", doc="The assigned Obj.")
    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the assigned Obj.",
    )

    comment = sa.Column(
        sa.String(),
        doc="A comment on the assignment. "
        "Typically a justification for the request, "
        "or instructions for taking the data.",
    )
    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending",
        doc="Status of the assignment [done, not done, pending].",
    )
    priority = sa.Column(
        followup_priorities,
        nullable=False,
        doc="Priority of the request (1 = lowest, 5 = highest).",
    )
    spectra = relationship(
        "Spectrum",
        back_populates="assignment",
        doc="Spectra produced by the assignment.",
    )
    photometry = relationship(
        "Photometry",
        back_populates="assignment",
        doc="Photometry produced by the assignment.",
    )
    photometric_series = relationship(
        "PhotometricSeries",
        back_populates="assignment",
        doc="Photometric series produced by the assignment.",
    )

    run = relationship(
        "ObservingRun",
        back_populates="assignments",
        doc="The ObservingRun this target was assigned to.",
    )
    run_id = sa.Column(
        sa.ForeignKey("observingruns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the ObservingRun this target was assigned to.",
    )

    @hybrid_property
    def instrument(self):
        """The instrument in use on the assigned ObservingRun."""
        return self.run.instrument

    @property
    def rise_time(self):
        """The UTC time at which the object rises on this run."""
        target = self.obj.target
        return self.run.rise_time(target)

    @property
    def set_time(self):
        """The UTC time at which the object sets on this run."""
        target = self.obj.target
        return self.run.set_time(target)
