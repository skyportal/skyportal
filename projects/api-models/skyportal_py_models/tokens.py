"""Response models for ``/api/internal/tokens``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiTokenResponse(BaseModel):
    """An API token (baselayer ``Token``).

    ``acls`` are the full ACL rows and ``created_by`` the owner's
    ``User.to_dict()``, both eager-loaded by the token endpoints.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime | None = None
    modified: datetime | None = None
    created_by_id: int | None = None
    created_by: dict[str, Any] | None = None
    name: str | None = None
    acls: list[dict[str, Any]] = Field(default_factory=list)
