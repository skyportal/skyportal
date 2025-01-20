__all__ = [
    "RecurringAPI",
]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
    accessible_by_owner,
)


class RecurringAPI(Base):
    """A Recurring API call by a User."""

    create = read = update = delete = accessible_by_owner

    owner_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        doc="The ID of the User that made the Recurring API call.",
    )
    owner = relationship(
        "User",
        back_populates="recurring_apis",
        lazy="selectin",
        doc="The User that made the Recurring API call.",
    )

    endpoint = sa.Column(
        sa.String,
        nullable=False,
        doc="The endpoint of the API call.",
    )

    payload = sa.Column(JSONB, doc="API call data in JSON format.", nullable=False)

    method = sa.Column(
        sa.String,
        nullable=False,
        doc="The HTTP method of the API call.",
    )

    next_call = sa.Column(
        sa.DateTime, nullable=False, index=True, doc="Time of the next API call."
    )

    call_delay = sa.Column(
        sa.Float, nullable=False, doc="Delay until next API call in days."
    )

    number_of_retries = sa.Column(
        sa.Integer, nullable=False, default=10, doc="Number of remaining API retries."
    )

    active = sa.Column(
        sa.Boolean(),
        nullable=False,
        server_default="true",
        doc="Boolean indicating whether this Recurring API remains active.",
    )
