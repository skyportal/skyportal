"""Response models for ``/api/assistant/messages`` and
``/api/assistant/conversations``."""

# ``GET /api/assistant/conversations`` returns a bare ``list[str]`` of channel
# names, so it needs no model.

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssistantMessageResponse(BaseModel):
    """One message of an assistant conversation.

    ``channel`` is null for the default conversation; ``context_type`` and
    ``context_id`` name the resource the conversation was opened on, if any.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    user_id: int | None = None
    channel: str | None = None
    text: str | None = None
    system: bool | None = None
    context_type: str | None = None
    context_id: str | None = None


class AssistantMessagePostResponse(BaseModel):
    """Result of sending a message to the assistant."""

    model_config = ConfigDict(extra="forbid")

    id: int


__all__ = [
    "AssistantMessagePostResponse",
    "AssistantMessageResponse",
]
