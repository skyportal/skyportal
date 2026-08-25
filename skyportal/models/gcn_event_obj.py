__all__ = ["GcnEventObj"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.env import load_env
from baselayer.app.models import (
    AccessibleIfRelatedRowsAreAccessible,
    Base,
)

from ..enum_types import gcn_event_obj_statuses

_, cfg = load_env()


class GcnEventObj(Base):
    """An Obj's standing against a GcnEvent: proposed, ruled on, or rejected."""

    # Scoped to the event: the row ties an obj to a dateobs, so a public read
    # would disclose a restricted event's existence, time and (via the public
    # Obj) position -- see /api/associated_gcns.
    #
    # Vetting is not behind a GCN-specific ACL: anyone who can see both the
    # event and the object is in a position to judge the association. The
    # handler still requires "Upload data", so read-only accounts stay so.
    read = create = update = delete = AccessibleIfRelatedRowsAreAccessible(
        gcnevent="read", obj="read"
    )

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Obj.",
    )

    obj = relationship(
        "Obj",
        back_populates="gcn_events",
        doc="The assigned Obj.",
    )

    dateobs = sa.Column(
        sa.DateTime,
        sa.ForeignKey("gcnevents.dateobs", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="UTC event timestamp",
    )

    gcnevent = relationship(
        "GcnEvent",
        doc="The GcnEvent this association belongs to.",
    )

    status = sa.Column(
        gcn_event_obj_statuses,
        nullable=False,
        server_default="pending",
        index=True,
        doc="Standing of this obj against the event: 'pending' (proposed, "
        "awaiting review), 'confirmed', 'ambiguous' (reviewed, undecided) "
        "or 'rejected'.",
    )

    # the person who recorded the association
    confirmer = relationship(
        "User",
        back_populates="gcn_event_objs",
        doc="The User who created this GcnEventObj.",
        foreign_keys="GcnEventObj.confirmer_id",
    )
    confirmer_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The ID of the User who created this GcnEventObj.",
    )

    explanation = sa.Column(
        sa.String,
        doc="Explanation on the nature of confirmation or rejection.",
    )

    notes = sa.Column(
        sa.String,
        doc="Extra information about the source.",
    )
