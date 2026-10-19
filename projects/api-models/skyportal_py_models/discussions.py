"""Request and response models for ``/api/discussions`` and ``/api/comment_threads``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DiscussionPostBody(BaseModel):
    """Request body for starting a discussion."""

    model_config = ConfigDict(extra="forbid")

    direct: bool = Field(
        default=False,
        description="Open (or reopen) a direct message with the single user in user_ids.",
    )
    user_ids: list[int] = Field(default_factory=list, description="Users to talk with.")
    group_id: int | None = Field(
        default=None,
        description="Group whose members all take part, instead of chosen users.",
    )
    name: str | None = Field(default=None, max_length=200)


class DiscussionPatchBody(BaseModel):
    """Request body for renaming a discussion."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class DiscussionMembersPostBody(BaseModel):
    """Request body for adding users to a discussion."""

    model_config = ConfigDict(extra="forbid")

    user_ids: list[int] = Field(min_length=1)


class DiscussionMembershipPatchBody(BaseModel):
    """Request body for the requesting user's own state in a discussion."""

    model_config = ConfigDict(extra="forbid")

    muted: bool | None = Field(
        default=None, description="Stop or resume notifications for this discussion."
    )
    read: bool | None = Field(default=None, description="Mark every message as read.")


class DiscussionMessageListQuery(BaseModel):
    """Query parameters for reading a discussion, latest messages first."""

    model_config = ConfigDict(extra="forbid")

    before: int | None = Field(
        default=None, description="Only messages older than this message ID."
    )
    limit: int = Field(default=50, ge=1, le=200)


class DiscussionMessagePostBody(BaseModel):
    """Request body for sending or editing a message."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=10000)


class DiscussionUserResponse(BaseModel):
    """A user taking part in a discussion."""

    model_config = ConfigDict(extra="forbid")

    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None
    gravatar_url: str | None = None
    is_bot: bool = False


class DiscussionMessageResponse(BaseModel):
    """A message of a discussion."""

    model_config = ConfigDict(extra="forbid")

    id: int
    discussion_id: int
    text: str
    created_at: datetime
    modified: datetime
    author: DiscussionUserResponse


class DiscussionGroupResponse(BaseModel):
    """The group whose members take part in a discussion."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str


class DiscussionResponse(BaseModel):
    """A discussion, as seen by the requesting user."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str | None = None
    is_direct: bool
    creator_id: int | None = None
    created_at: datetime
    group: DiscussionGroupResponse | None = None
    members: list[DiscussionUserResponse] = Field(
        default_factory=list,
        description="Chosen members; empty for a group discussion.",
    )
    member_count: int
    muted: bool
    unread: int
    last_message: DiscussionMessageResponse | None = None


class DiscussionListResponse(BaseModel):
    """The discussions the requesting user takes part in, latest activity first."""

    model_config = ConfigDict(extra="forbid")

    discussions: list[DiscussionResponse] = Field(default_factory=list)


class DiscussionMemberListResponse(BaseModel):
    """The users taking part in a discussion."""

    model_config = ConfigDict(extra="forbid")

    members: list[DiscussionUserResponse] = Field(default_factory=list)


class DiscussionMessageListResponse(BaseModel):
    """A page of the messages of a discussion, oldest first."""

    model_config = ConfigDict(extra="forbid")

    messages: list[DiscussionMessageResponse] = Field(default_factory=list)
    has_more: bool = Field(description="Whether older messages remain.")


class DiscussionPostResponse(BaseModel):
    """The discussion started, or the existing direct message."""

    model_config = ConfigDict(extra="forbid")

    id: int


class CommentThreadLastCommentResponse(BaseModel):
    """The latest comment of a thread."""

    model_config = ConfigDict(extra="forbid")

    id: int
    text: str
    created_at: datetime
    author: DiscussionUserResponse


class CommentThreadResponse(BaseModel):
    """A comment thread the requesting user wrote in."""

    model_config = ConfigDict(extra="forbid")

    resource_type: Literal["sources", "gcn_event", "earthquake", "shift"]
    resource_id: str
    label: str
    url: str
    channel: str | None = None
    last_comment: CommentThreadLastCommentResponse
    dateobs: str | None = Field(default=None, description="GCN events only.")
    event_id: str | None = Field(default=None, description="Earthquakes only.")


class CommentThreadListResponse(BaseModel):
    """Comment threads the requesting user is involved in, latest activity first."""

    model_config = ConfigDict(extra="forbid")

    threads: list[CommentThreadResponse] = Field(default_factory=list)


__all__ = [
    "CommentThreadLastCommentResponse",
    "CommentThreadListResponse",
    "CommentThreadResponse",
    "DiscussionGroupResponse",
    "DiscussionListResponse",
    "DiscussionMemberListResponse",
    "DiscussionMembersPostBody",
    "DiscussionMembershipPatchBody",
    "DiscussionMessageListQuery",
    "DiscussionMessageListResponse",
    "DiscussionMessagePostBody",
    "DiscussionMessageResponse",
    "DiscussionPatchBody",
    "DiscussionPostBody",
    "DiscussionPostResponse",
    "DiscussionResponse",
    "DiscussionUserResponse",
]
