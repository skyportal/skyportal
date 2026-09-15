"""Response models for ``/api/listing``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ListingResponse(BaseModel):
    """An object saved by a user to a named list (``Listing``)."""

    # The handler returns bare ``Listing`` rows, so the ``user`` and ``obj``
    # relationships are never loaded and are not declared here.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    user_id: int | None = None
    obj_id: str | None = None
    list_name: str | None = None
    params: dict[str, Any] | None = None
