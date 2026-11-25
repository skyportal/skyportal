"""Request and response models for ``/api/feedback``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FeedbackCategory = Literal["bug", "change", "other"]


class FeedbackPostBody(BaseModel):
    """Request body for leaving a message to the admins."""

    model_config = ConfigDict(extra="forbid")

    category: FeedbackCategory = Field(
        description="bug report, change request, or other"
    )
    text: str = Field(min_length=1, max_length=10000, description="The message")


class FeedbackPatchBody(BaseModel):
    """Request body for marking a message as handled, or assigning it to an admin."""

    model_config = ConfigDict(extra="forbid")

    resolved: bool | None = None
    assignee_id: int | None = Field(
        default=None, description="ID of the admin working on it; null to unassign"
    )
    pr_urls: list[str] | None = Field(
        default=None,
        max_length=20,
        description="GitHub pull requests fixing it; the author is notified once all are deployed",
    )


class FeedbackReplyPostBody(BaseModel):
    """Request body for replying to a message, as an admin or its author."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=10000, description="The reply")


class FeedbackAuthorResponse(BaseModel):
    """The user who wrote a message or a reply."""

    model_config = ConfigDict(extra="forbid")

    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None
    gravatar_url: str | None = None


class FeedbackReplyResponse(BaseModel):
    """A reply to a message, from an admin or its author."""

    model_config = ConfigDict(extra="forbid")

    id: int
    text: str
    created_at: datetime
    author: FeedbackAuthorResponse


class FeedbackPullRequestResponse(BaseModel):
    """A pull request linked to a message, and whether this instance runs it."""

    model_config = ConfigDict(extra="forbid")

    url: str
    deployed: bool


class FeedbackResponse(BaseModel):
    """A message left to the admins, with their replies."""

    model_config = ConfigDict(extra="forbid")

    id: int
    category: FeedbackCategory
    text: str
    resolved: bool
    created_at: datetime
    author: FeedbackAuthorResponse
    assignee: FeedbackAuthorResponse | None = None
    replies: list[FeedbackReplyResponse] = Field(default_factory=list)
    pull_requests: list[FeedbackPullRequestResponse] = Field(default_factory=list)
    deployed_at: datetime | None = None


class FeedbackListResponse(BaseModel):
    """The messages the requesting user can read: their own, or all for admins."""

    model_config = ConfigDict(extra="forbid")

    messages: list[FeedbackResponse] = Field(default_factory=list)


__all__ = [
    "FeedbackAuthorResponse",
    "FeedbackCategory",
    "FeedbackListResponse",
    "FeedbackPatchBody",
    "FeedbackPostBody",
    "FeedbackPullRequestResponse",
    "FeedbackReplyPostBody",
    "FeedbackReplyResponse",
    "FeedbackResponse",
]
