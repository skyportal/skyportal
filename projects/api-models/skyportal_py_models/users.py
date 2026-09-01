"""Response models for ``/api/user``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import UserResponse


class UsersPageResponse(BaseModel):
    """One page of results from a users query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    users: list[UserResponse]
    total_matches: int = Field(alias="totalMatches")


class UserPost(BaseModel):
    """Payload for adding a new user."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    username: str
    first_name: str | None = None
    last_name: str | None = None
    affiliations: list[str] | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    oauth_uid: str | None = None
    roles: list[str] | None = None
    group_ids_and_admin: list[list[int | bool]] | None = Field(
        alias="groupIDsAndAdmin", default=None
    )


__all__ = [
    "UserPost",
    "UserResponse",
    "UsersPageResponse",
]
