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


class TokenPostBody(BaseModel):
    """Request body for creating a new API token."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Name of the token")
    acls: list[str] = Field(description="List of ACL IDs to grant the token")
    user_id: int | None = Field(
        default=None,
        description="ID of the user to create the token for; defaults to the requesting user",
    )


class TokenPostResponse(BaseModel):
    """ID of the newly created token."""

    token_id: str = Field(description="Token ID")


class TokenPutBody(BaseModel):
    """Request body for updating a token."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="New name of the token")
    acls: list[str] | None = Field(
        default=None, description="New list of ACL IDs for the token"
    )
    user_id: int | None = Field(
        default=None,
        description="ID of the user whose permissions the new ACLs are checked against; defaults to the requesting user",
    )
