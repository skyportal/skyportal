__all__ = ["GcnEventAssociation"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    AccessibleIfRelatedRowsAreAccessible,
    Base,
)

from ..enum_types import gcn_event_obj_statuses


class GcnEventAssociation(Base):
    """Two GcnEvents proposed as the same physical event.

    The pair is stored once, ordered by dateobs, so a coincidence is one row
    rather than a row per direction.

    ``overlap`` and ``dt_days`` are objective and computed once; the cuts that
    turn them into a verdict differ by science case (a neutrino-GW pair is
    judged on a much tighter window than a GRB-GW one), so they are applied when
    the associations are read, not when they are found.
    """

    # Keyed on the earlier event only: joining gcnevents twice in one policy
    # collides on the table name. Readers must still be able to see both, so the
    # handler drops any row whose partner event it cannot load.
    read = create = update = delete = AccessibleIfRelatedRowsAreAccessible(
        gcnevent_1="read"
    )

    dateobs_1 = sa.Column(
        sa.DateTime,
        sa.ForeignKey("gcnevents.dateobs", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="UTC timestamp of the earlier event.",
    )

    dateobs_2 = sa.Column(
        sa.DateTime,
        sa.ForeignKey("gcnevents.dateobs", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="UTC timestamp of the later event.",
    )

    gcnevent_1 = relationship(
        "GcnEvent",
        foreign_keys="GcnEventAssociation.dateobs_1",
        doc="The earlier GcnEvent.",
    )

    gcnevent_2 = relationship(
        "GcnEvent",
        foreign_keys="GcnEventAssociation.dateobs_2",
        doc="The later GcnEvent.",
    )

    overlap = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc="RAVEN sky-map overlap integral: 1 is what unrelated maps average, "
        "higher means the localizations agree more than chance.",
    )

    consistency = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc="Overlap as a fraction of the most these two maps could overlap "
        "(their correlation): 1 when they agree as well as localizations of "
        "these shapes can, 0 when disjoint. Comparable across pairs, which the "
        "raw overlap is not -- its ceiling is set by the localization areas.",
    )

    dt_days = sa.Column(
        sa.Float,
        nullable=False,
        doc="dateobs_2 - dateobs_1, in days. Always positive.",
    )

    status = sa.Column(
        gcn_event_obj_statuses,
        nullable=False,
        server_default="pending",
        index=True,
        doc="Standing of this association: 'pending' (proposed, awaiting "
        "review), 'confirmed', 'ambiguous' (reviewed, undecided) or 'rejected'.",
    )

    confirmer = relationship(
        "User",
        doc="The User who last ruled on this association.",
        foreign_keys="GcnEventAssociation.confirmer_id",
    )
    confirmer_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The ID of the User who last ruled on this association.",
    )

    explanation = sa.Column(
        sa.String,
        doc="Why this association was confirmed or rejected.",
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "dateobs_1", "dateobs_2", name="gcneventassociations_dateobs_pair_key"
        ),
        sa.CheckConstraint("dateobs_1 < dateobs_2", name="gcneventassociations_order"),
    )
