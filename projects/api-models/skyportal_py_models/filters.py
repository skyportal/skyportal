"""Response models for ``/api/filters``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


class FilterPostBody(BaseModel):
    """Request body for creating a filter."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Filter name.")
    stream_id: int = Field(description="ID of the Filter's Stream.")
    group_id: int = Field(description="ID of the Filter's Group.")
    broker_id: int | None = Field(
        default=None,
        description="ID of the Broker this Filter runs on, if any.",
    )
    altdata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary additional JSON data associated with the Filter.",
    )


class FilterPostResponse(BaseModel):
    """Data payload returned when creating a filter."""

    id: int = Field(description="New filter ID")


class FilterPatchBody(BaseModel):
    """Request body for updating a filter."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Filter name.")
    altdata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary additional JSON data associated with the Filter.",
    )
    group_id: int | None = Field(
        default=None,
        description="ID of the Filter's Group. Cannot be changed; accepted "
        "only if it matches the current value.",
    )
    stream_id: int | None = Field(
        default=None,
        description="ID of the Filter's Stream. Cannot be changed; accepted "
        "only if it matches the current value.",
    )
    broker_id: int | None = Field(
        default=None,
        description="ID of the Broker this Filter runs on. Can only be set "
        "while the filter has none: moving a filter between brokers would "
        "orphan whatever the first one holds for it.",
    )
    autosave: bool | None = Field(
        default=None,
        description="Whether objects passing this filter during broker ingestion "
        "are auto-saved as Sources to the Filter's Group.",
    )


class FilterGetQuery(BaseModel):
    """Query parameters for listing filters."""

    model_config = ConfigDict(extra="forbid")

    group_id: int | None = Field(
        default=None,
        description="Only return filters belonging to this Group.",
    )
    stream_id: int | None = Field(
        default=None,
        description="Only return filters reading from this Stream.",
    )
