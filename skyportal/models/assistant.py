__all__ = ["AssistantMessage"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base


class AssistantMessage(Base):
    """One message in a user's conversation with the assistant."""

    create = read = update = delete = AccessibleIfUserMatches("user")

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User the conversation belongs to.",
    )

    user = relationship(
        "User",
        back_populates="assistant_messages",
        foreign_keys=[user_id],
        doc="The User the conversation belongs to.",
    )

    channel = sa.Column(
        sa.String,
        nullable=True,
        index=True,
        doc="Conversation the message belongs to, NULL for the default one.",
    )

    text = sa.Column(sa.String, nullable=False, doc="Message body.")

    system = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether the assistant wrote the message rather than the user.",
    )

    context_type = sa.Column(
        sa.String,
        nullable=True,
        doc="Kind of resource the user was looking at when they asked, if any.",
    )

    context_id = sa.Column(sa.String, nullable=True, doc="ID of that resource, if any.")
