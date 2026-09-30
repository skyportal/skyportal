__all__ = ["Feedback"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base, restricted


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
