"""Response models for ``/api/streams``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class StreamResponse(BaseModel):
    """An alert stream, e.g. a survey's public alerts."""

    # No handler eager-loads Stream.groups/users/filters/photometry, so those
    # relationships never appear in a serialized Stream and are not declared.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str
    altdata: dict[str, Any] | None = None
    auto_join: bool | None = None
