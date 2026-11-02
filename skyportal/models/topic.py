__all__ = ["Topic", "TopicSource", "TopicSubscription"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base


class Topic(Base):
    """A theme users subscribe to: the sources matching it, and their activity."""

    update = delete = AccessibleIfUserMatches("creator")

    name = sa.Column(sa.String, nullable=False, unique=True, doc="Name of the topic.")
    description = sa.Column(sa.String, nullable=True, doc="What the topic is about.")
    creator_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the User who created the topic.",
    )
    creator = relationship("User", doc="The User who created the topic.")
    classifications = sa.Column(
        sa.ARRAY(sa.String),
        nullable=False,
        server_default="{}",
        doc="Human classifications that bring a source into the topic.",
    )
    tag_ids = sa.Column(
        sa.ARRAY(sa.Integer),
        nullable=False,
        server_default="{}",
        doc="IDs of the object tags that bring a source into the topic.",
    )
    subscriptions = relationship(
        "TopicSubscription",
        back_populates="topic",
        cascade="all, delete-orphan",
        passive_deletes=True,
        doc="Subscriptions of users to the topic.",
    )
    sources = relationship(
        "TopicSource",
        back_populates="topic",
        cascade="all, delete-orphan",
        passive_deletes=True,
        doc="Sources posted to the topic by users.",
    )


class TopicSubscription(Base):
    """A user following a topic."""

    __tablename__ = "topic_subscriptions"

    create = read = update = delete = AccessibleIfUserMatches("user")

    topic_id = sa.Column(
        sa.ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Topic.",
    )
    topic = relationship("Topic", back_populates="subscriptions", doc="The Topic.")
    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the subscriber.",
    )
    user = relationship("User", doc="The subscriber.")

    __table_args__ = (
        sa.UniqueConstraint("topic_id", "user_id", name="topic_subscription_uniq"),
    )


class TopicSource(Base):
    """A source posted to a topic by a user."""

    __tablename__ = "topic_sources"

    create = AccessibleIfUserMatches("author")
    update = delete = AccessibleIfUserMatches("author") | AccessibleIfUserMatches(
        "topic.creator"
    )

    topic_id = sa.Column(
        sa.ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Topic.",
    )
    topic = relationship("Topic", back_populates="sources", doc="The Topic.")
    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the posted Obj.",
    )
    obj = relationship("Obj", doc="The posted Obj.")
    author_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User who posted the source.",
    )
    author = relationship("User", doc="The User who posted the source.")
    text = sa.Column(
        sa.String, nullable=True, doc="Why the source belongs in the topic."
    )

    __table_args__ = (
        sa.UniqueConstraint("topic_id", "obj_id", name="topic_source_uniq"),
    )
