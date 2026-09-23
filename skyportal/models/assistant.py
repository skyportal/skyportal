__all__ = ["AssistantMessage", "AssistantQuery", "AssistantQuerySubscription"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
    Base,
)

from .group import accessible_by_group_members


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

    notify = sa.Column(
        JSONB,
        nullable=True,
        doc="Who to notify with the answer, as {'users': [ids], 'groups': [ids]}. "
        "Used by scheduled/triggered runs; a person chatting reads it in the panel.",
    )

    tool_calls = sa.Column(
        JSONB,
        nullable=True,
        doc="The tools the assistant ran to reach this answer, in order, as "
        "[{name, arguments, ok, summary}]. Shown so the reader can see what "
        "the answer rests on rather than taking the prose for it.",
    )

    proposal = sa.Column(
        JSONB,
        nullable=True,
        doc="A filter pipeline the assistant arrived at, with whatever preview "
        "it ran, so the page can offer it for saving. Read out of tool_calls.",
    )


class AssistantQuery(Base):
    """A shared, group-scoped assistant task others can discover and subscribe to.

    A completed analysis whose service name contains ``analysis_service_match``
    triggers a skybot run of ``prompt`` on the source; the answer is delivered to
    the subscribers who are members of ``group``, plus any always-on
    ``notify_groups``. Personal one-off schedules stay in RecurringAPI; this is
    the shared, subscribable kind.
    """

    __tablename__ = "assistantqueries"

    read = accessible_by_group_members
    create = accessible_by_group_members
    update = delete = AccessibleIfUserMatches("owner")

    owner_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User who created the query.",
    )
    owner = relationship(
        "User", foreign_keys=[owner_id], doc="User who created the query."
    )

    group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Group the query is tied to; its members can see and subscribe.",
    )
    group = relationship("Group", doc="Group the query is tied to.")

    name = sa.Column(sa.String, nullable=False, doc="Short name shown in the list.")
    description = sa.Column(sa.String, nullable=True, doc="What the query does.")
    prompt = sa.Column(
        sa.String, nullable=False, doc="Instruction run by the assistant."
    )
    context_type = sa.Column(
        sa.String,
        nullable=False,
        server_default="source",
        doc="Resource the query runs on (currently 'source').",
    )

    analysis_service_match = sa.Column(
        sa.String,
        nullable=True,
        index=True,
        doc="Substring of an analysis service name; a completed matching analysis "
        "triggers the query. NULL for a query that is not analysis-triggered.",
    )

    notify_groups = sa.Column(
        JSONB,
        nullable=True,
        doc="Group ids always notified with the answer, besides the subscribers.",
    )

    active = sa.Column(
        sa.Boolean, nullable=False, server_default="true", doc="Whether the query runs."
    )
    dry_run = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Run but notify no one (validation mode).",
    )

    subscriptions = relationship(
        "AssistantQuerySubscription",
        back_populates="query",
        cascade="all, delete-orphan",
        passive_deletes=True,
        doc="Per-user notification subscriptions.",
    )


class AssistantQuerySubscription(Base):
    """A user's opt-in to be notified by an AssistantQuery."""

    # You can only subscribe (with yourself) to a query you can read, i.e. one in
    # a group you belong to.
    create = AccessibleIfRelatedRowsAreAccessible(
        query="read"
    ) & AccessibleIfUserMatches("user")
    read = update = delete = AccessibleIfUserMatches("user")

    query_id = sa.Column(
        sa.ForeignKey("assistantqueries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The query subscribed to.",
    )
    query = relationship(
        "AssistantQuery", back_populates="subscriptions", doc="The query subscribed to."
    )

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The subscribing user.",
    )
    user = relationship("User", foreign_keys=[user_id], doc="The subscribing user.")

    __table_args__ = (
        sa.UniqueConstraint(
            "query_id", "user_id", name="assistant_query_subscription_uniq"
        ),
    )
