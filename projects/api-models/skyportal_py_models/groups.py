"""Response models for ``/api/groups``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import (
    GroupMemberResponse,
    GroupResponse,
    GroupUserResponse,
)


class GroupsResponse(BaseModel):
    """The groups visible to the token, split by relationship to the user."""

    model_config = ConfigDict(extra="forbid")

    user_groups: list[GroupResponse] = Field(default_factory=list)
    user_accessible_groups: list[GroupResponse] = Field(default_factory=list)
    all_groups: list[GroupResponse] | None = None


class GroupPost(BaseModel):
    """Payload for creating a group."""

    model_config = ConfigDict(extra="forbid")

    name: str
    nickname: str | None = None
    description: str | None = None
    auto_accept_requests: bool | None = None
    group_admins: list[int] | None = None


__all__ = [
    "GroupPost",
    "GroupMemberResponse",
    "GroupResponse",
    "GroupUserResponse",
    "GroupsResponse",
]
