"""Response models for ``/api/user``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import UserResponse


class UsersPageResponse(BaseModel):
    """One page of results from a users query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    users: list[UserResponse]
    total_matches: int = Field(alias="totalMatches")


__all__ = [
    "UserResponse",
    "UsersPageResponse",
]
