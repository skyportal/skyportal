__all__ = ["Candidate"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base


class Candidate(Base):
    "An Obj that passed a Filter, becoming scannable on the Filter's scanning page."

    create = read = update = delete = AccessibleIfUserMatches(
        "filter.group.group_users.user"
    )

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Obj",
    )
    obj = relationship(
        "Obj",
        foreign_keys=[obj_id],
        back_populates="candidates",
        doc="The Obj that passed a filter",
    )
    filter_id = sa.Column(
        sa.ForeignKey("filters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the filter the candidate passed",
    )
    filter = relationship(
        "Filter",
        foreign_keys=[filter_id],
        back_populates="candidates",
        doc="The filter that the Candidate passed",
    )
    passed_at = sa.Column(
        sa.DateTime,
        nullable=False,
        index=True,
        doc="ISO UTC time when the Candidate passed the Filter.",
    )
    passing_alert_id = sa.Column(
        sa.BigInteger,
        index=True,
        doc="ID of the latest Stream alert that passed the Filter.",
    )
    uploader_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user that posted the candidate",
    )


Candidate.__table_args__ = (
    sa.Index(
        "candidates_main_index",
        Candidate.obj_id,
        Candidate.filter_id,
        Candidate.passed_at,
        unique=True,
    ),
)
