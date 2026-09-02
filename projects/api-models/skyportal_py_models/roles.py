"""Response models for ``/api/roles``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleResponse(BaseModel):
    """A named collection of ACLs (the baselayer ``Role`` model)."""

    # The handler replaces the ``acls`` relationship with a list of ACL IDs.

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime | None = None
    modified: datetime | None = None
    acls: list[str] = Field(default_factory=list)


class UserRolePostBody(BaseModel):
    """Request body for granting roles to a user."""

    model_config = ConfigDict(extra="forbid")

    roleIds: list[str] = Field(
        description="Array of Role IDs (strings) to be granted to user"
    )
