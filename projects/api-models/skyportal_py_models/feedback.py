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
    """Request body for marking a message as handled."""

    model_config = ConfigDict(extra="forbid")

    resolved: bool


class FeedbackAuthorResponse(BaseModel):
    """The user who wrote a message."""

    model_config = ConfigDict(extra="forbid")

    id: int
    username: str


class FeedbackResponse(BaseModel):
    """A message left to the admins."""

    model_config = ConfigDict(extra="forbid")

    id: int
    category: FeedbackCategory
    text: str
    resolved: bool
    created_at: datetime
    author: FeedbackAuthorResponse


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
    "FeedbackResponse",
]
