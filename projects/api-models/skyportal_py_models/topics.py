"""Request and response models for ``/api/topics``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.discussions import DiscussionUserResponse


class TopicPostBody(BaseModel):
    """Request body for creating a topic."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    classifications: list[str] = Field(
        default_factory=list,
        description="Human classifications that bring a source into the topic.",
    )
    tag_ids: list[int] = Field(
        default_factory=list,
        description="Object tags that bring a source into the topic.",
    )


class TopicPatchBody(BaseModel):
    """Request body for editing a topic. Restricted to its creator."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    classifications: list[str] | None = None
    tag_ids: list[int] | None = None


class TopicSourcePostBody(BaseModel):
    """Request body for posting a source to a topic."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str = Field(min_length=1)
    text: str | None = Field(default=None, max_length=2000)


class TopicFeedQuery(BaseModel):
    """Query parameters for a topic feed, latest first."""

    model_config = ConfigDict(extra="forbid")

    topic_id: int | None = Field(
        default=None, description="One topic, instead of every subscribed topic."
    )
    before: datetime | None = Field(
        default=None, description="Only items older than this time."
    )
    limit: int = Field(default=20, ge=1, le=100)


class TopicTagResponse(BaseModel):
    """An object tag that brings sources into a topic."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    color: str | None = None


class TopicResponse(BaseModel):
    """A topic, as seen by the requesting user."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    description: str | None = None
    creator: DiscussionUserResponse | None = None
    created_at: datetime
    classifications: list[str] = Field(default_factory=list)
    tags: list[TopicTagResponse] = Field(default_factory=list)
    subscriber_count: int
    subscribed: bool


class TopicListResponse(BaseModel):
    """Every topic, most followed first."""

    model_config = ConfigDict(extra="forbid")

    topics: list[TopicResponse] = Field(default_factory=list)


class TopicIdResponse(BaseModel):
    """The ID of the created record."""

    model_config = ConfigDict(extra="forbid")

    id: int


class TopicFeedItemResponse(BaseModel):
    """Something that happened to a source of a topic."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["post", "classification", "tag", "comment", "spectrum"]
    id: int = Field(
        description="ID of the post, classification, tag, comment or spectrum."
    )
    time: datetime
    obj_id: str
    author: DiscussionUserResponse | None = None
    text: str | None = Field(default=None, description="Posts and comments.")
    label: str | None = Field(
        default=None,
        description="The classification, the tag, or the spectrum's instrument.",
    )
    topic_ids: list[int] = Field(
        default_factory=list, description="Requested topics the source belongs to."
    )


class TopicFeedResponse(BaseModel):
    """A page of a topic feed, latest first."""

    model_config = ConfigDict(extra="forbid")

    items: list[TopicFeedItemResponse] = Field(default_factory=list)
    has_more: bool = Field(description="Whether older items remain.")


__all__ = [
    "TopicFeedItemResponse",
    "TopicFeedQuery",
    "TopicFeedResponse",
    "TopicIdResponse",
    "TopicListResponse",
    "TopicPatchBody",
    "TopicPostBody",
    "TopicResponse",
    "TopicSourcePostBody",
    "TopicTagResponse",
]
