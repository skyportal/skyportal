"""Response models for ``/api/filters``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from skyportal_py_models.streams import StreamResponse


class FilterResponse(BaseModel):
    """An alert-stream filter belonging to a group."""

    # The list endpoint returns only LIST_FIELDS; GET on a single filter also
    # returns altdata and the eagerly loaded stream.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    stream_id: int | None = None
    group_id: int | None = None
    broker_id: int | None = None
    altdata: dict[str, Any] | None = None
    autosave: bool | None = None
    stream: StreamResponse | None = None


class FilterPost(BaseModel):
    """Payload for creating a filter."""

    model_config = ConfigDict(extra="forbid")

    name: str
    stream_id: int
    group_id: int
    broker_id: int | None = None
    altdata: dict[str, Any] | None = None


class FilterPatch(BaseModel):
    """Payload for updating a filter."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    altdata: dict[str, Any] | None = None
    group_id: int | None = None
    stream_id: int | None = None
    autosave: bool | None = None
