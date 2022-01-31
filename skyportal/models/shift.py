__all__ = ['Shift']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base

from .group import accessible_by_group_members


class Shift(Base):
    """A scanning shift. A Shift is associated
    with exactly one Group, and a Group may have multiple operational Shifts.
    """

    # TODO: Track shift ownership and allow owners to update, delete shifts
    create = read = update = delete = accessible_by_group_members

    group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Shift's Group.",
    )
    group = relationship(
        "Group",
        foreign_keys=[group_id],
        back_populates="shifts",
        doc="The Shift's Group.",
    )

    start_date = sa.Column(
        sa.DateTime, nullable=False, index=True, doc="The start time of this shift."
    )

    end_date = sa.Column(
        sa.DateTime, nullable=False, index=True, doc="The end time of this shift."
    )
