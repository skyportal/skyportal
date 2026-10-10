__all__ = ["Discussion", "DiscussionMember", "DiscussionMessage"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    AccessibleIfUserMatches,
    Base,
    CustomUserAccessControl,
    UserAccessControl,
)

from .group import GroupUser


def accessible_discussion_ids(user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    return sa.select(Discussion.id).where(
        sa.or_(
            sa.and_(
                Discussion.group_id.is_(None),
                Discussion.id.in_(
                    sa.select(DiscussionMember.discussion_id).where(
                        DiscussionMember.user_id == user_id
                    )
                ),
            ),
            Discussion.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            ),
        )
    )


accessible_by_participants = CustomUserAccessControl(
    lambda cls, user_or_token: sa.select(cls).where(
        cls.id.in_(accessible_discussion_ids(user_or_token))
    )
)
accessible_by_discussion_participants = CustomUserAccessControl(
    lambda cls, user_or_token: sa.select(cls).where(
        cls.discussion_id.in_(accessible_discussion_ids(user_or_token))
    )
)


class Discussion(Base):
    """A conversation between users: a direct message, a few chosen users, or a whole group."""

    read = update = accessible_by_participants
    delete = AccessibleIfUserMatches("creator")

    name = sa.Column(
        sa.String,
        nullable=True,
        doc="Name of the discussion, NULL for a direct message.",
    )
    is_direct = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether this is a direct message between two users.",
    )
    creator_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the User who started the discussion.",
    )
    creator = relationship("User", doc="The User who started the discussion.")
    group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Group whose members all take part in the discussion, if any.",
    )
    group = relationship("Group", doc="Group whose members take part, if any.")
    members = relationship(
        "DiscussionMember",
        back_populates="discussion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        doc="Members of the discussion, and their read state.",
    )
    messages = relationship(
        "DiscussionMessage",
        back_populates="discussion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DiscussionMessage.created_at",
        doc="Messages of the discussion.",
    )


class DiscussionMember(Base):
    """A user taking part in a discussion. In a group discussion, only holds their read state."""

    __tablename__ = "discussion_members"

    create = read = accessible_by_discussion_participants
    update = AccessibleIfUserMatches("user")
    delete = AccessibleIfUserMatches("user") | AccessibleIfUserMatches(
        "discussion.creator"
    )

    discussion_id = sa.Column(
        sa.ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Discussion.",
    )
    discussion = relationship(
        "Discussion", back_populates="members", doc="The Discussion."
    )
    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the member.",
    )
    user = relationship("User", doc="The member.")
    last_read_at = sa.Column(
        sa.DateTime,
        nullable=True,
        doc="When the member last read the discussion.",
    )
    muted = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether the member is notified of new messages.",
    )

    __table_args__ = (
        sa.UniqueConstraint("discussion_id", "user_id", name="discussion_member_uniq"),
    )


class DiscussionMessage(Base):
    """A message posted in a discussion."""

    __tablename__ = "discussion_messages"

    read = accessible_by_discussion_participants
    create = accessible_by_discussion_participants & AccessibleIfUserMatches("author")
    update = delete = AccessibleIfUserMatches("author")

    discussion_id = sa.Column(
        sa.ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Discussion.",
    )
    discussion = relationship(
        "Discussion", back_populates="messages", doc="The Discussion."
    )
    author_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User who wrote the message.",
    )
    author = relationship("User", doc="The User who wrote the message.")
    text = sa.Column(sa.String, nullable=False, doc="Message body.")
