"""Response models for ``/api/streams``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class StreamPostBody(BaseModel):
    """Request body for creating a stream."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Stream name.")
    altdata: dict[str, Any] | None = Field(
        default=None,
        description="Misc. metadata stored in JSON format, e.g. "
        "`{'collection': 'ZTF_alerts', selector: [1, 2]}`",
    )
    auto_join: bool = Field(
        default=False,
        description="Boolean indicating whether any user may add themselves "
        "to this stream. Auto-join streams are visible to all users.",
    )


class StreamPostResponse(BaseModel):
    """Data payload returned when creating a stream."""

    id: int = Field(description="New stream ID")


class StreamPatchBody(BaseModel):
    """Request body for updating a stream."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Stream name.")
    altdata: dict[str, Any] | None = Field(
        default=None,
        description="Misc. metadata stored in JSON format, e.g. "
        "`{'collection': 'ZTF_alerts', selector: [1, 2]}`",
    )
    auto_join: bool | None = Field(
        default=None,
        description="Boolean indicating whether any user may add themselves "
        "to this stream. Auto-join streams are visible to all users.",
    )


class StreamUserPostBody(BaseModel):
    """Request body for granting stream access to a user."""

    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(description="ID of the user to be granted stream access")


class StreamUserPostResponse(BaseModel):
    """Data payload returned when granting stream access to a user."""

    stream_id: int = Field(description="Stream ID")
    user_id: int = Field(description="User ID")
