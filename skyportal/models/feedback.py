__all__ = ["Feedback", "FeedbackReply"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
    Base,
    restricted,
)


class Feedback(Base):
    """A message a user leaves the admins: a bug report, a change request..."""

    create = read = AccessibleIfUserMatches("author")
    update = delete = restricted

    author_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User who wrote the message",
    )
    author = relationship("User", doc="The User who wrote the message")
    category = sa.Column(
        sa.String, nullable=False, doc="Kind of message: bug, change or other"
    )
    text = sa.Column(sa.String, nullable=False, doc="The message")
    resolved = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether an admin has handled the message",
    )
    replies = relationship(
        "FeedbackReply",
        back_populates="feedback",
        cascade="delete",
        passive_deletes=True,
        order_by="FeedbackReply.created_at",
        doc="The admins' replies to the message",
    )


class FeedbackReply(Base):
    """An admin's reply to a message left by a user."""

    __tablename__ = "feedback_replies"

    read = AccessibleIfRelatedRowsAreAccessible(feedback="read")
    create = update = delete = restricted

    feedback_id = sa.Column(
        sa.ForeignKey("feedbacks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the message replied to",
    )
    feedback = relationship(
        "Feedback", back_populates="replies", doc="The message replied to"
    )
    author_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the admin who replied",
    )
    author = relationship("User", doc="The admin who replied")
    text = sa.Column(sa.String, nullable=False, doc="The reply")
