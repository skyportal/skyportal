"""Response models for ``/api/groups``."""

from __future__ import annotations

from typing import ClassVar

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


class GroupGetQuery(BaseModel):
    """Query parameters for retrieving groups."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"includeGroupUsers"})

    name: str | None = Field(
        default=None,
        description="Fetch by name (exact match)",
    )
    includeGroupUsers: bool = Field(
        default=True,
        description="Boolean indicating whether to include group users. Defaults to true.",
    )
    includeSingleUserGroups: bool = Field(
        default=False,
        description="Bool indicating whether to include single user groups. Defaults to false.",
    )


class GroupPostBody(BaseModel):
    """Request body for creating a group."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Name of the group.")
    nickname: str | None = Field(default=None, description="Short group nickname.")
    description: str | None = Field(
        default=None, description="Longer description of the group."
    )
    auto_accept_requests: bool | None = Field(
        default=None,
        description="Boolean indicating whether requests to join the group are "
        "automatically accepted.",
    )
    group_admins: list[int] | None = Field(
        default=None,
        description="List of IDs of users to be group admins. Current user will "
        "automatically be added as a group admin.",
    )


class GroupPostResponse(BaseModel):
    """Data payload returned when creating a group."""

    id: int = Field(description="New group ID")


class GroupPutBody(BaseModel):
    """Request body for updating a group."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Name of the group.")
    nickname: str | None = Field(default=None, description="Short group nickname.")
    description: str | None = Field(
        default=None, description="Longer description of the group."
    )
    private: bool | None = Field(
        default=None,
        description="Boolean indicating whether group is invisible to non-members.",
    )
    auto_accept_requests: bool | None = Field(
        default=None,
        description="Boolean indicating whether requests to join the group are "
        "automatically accepted.",
    )
    discoverable_data: bool | None = Field(
        default=None,
        description="Whether non-members may be told that the group's photometry "
        "and spectra exist, and so ask for them. Data held only by groups with "
        "this off is never advertised.",
    )


class GroupUserPostBody(BaseModel):
    """Request body for adding a user to a group."""

    model_config = ConfigDict(extra="forbid")

    userID: int | None = Field(
        default=None, description="ID of the user to add to the group."
    )
    admin: bool = Field(
        default=False, description="Boolean indicating whether user is group admin."
    )
    canSave: bool = Field(
        default=True,
        description="Boolean indicating whether user can save sources to group. "
        "Defaults to true.",
    )
    canSharePhotometry: bool = Field(
        default=False,
        description="Boolean indicating whether user can share photometry points "
        "to other groups. Defaults to false.",
    )


class GroupUserPostResponse(BaseModel):
    """Data payload returned when adding a user to a group."""

    group_id: int = Field(description="Group ID")
    user_id: int = Field(description="User ID")
    admin: bool = Field(description="Boolean indicating whether user is group admin")


class GroupUserPatchBody(BaseModel):
    """Request body for updating a group user."""

    model_config = ConfigDict(extra="forbid")

    userID: int | None = Field(default=None, description="ID of the user to update.")
    admin: bool | None = Field(
        default=None,
        description="Boolean indicating whether user is group admin. Either this, "
        "`canSave` or `canSharePhotometry` must be provided in request body.",
    )
    canSave: bool | None = Field(
        default=None,
        description="Boolean indicating whether user can save sources to group. "
        "Either this, `admin` or `canSharePhotometry` must be provided in "
        "request body.",
    )
    canSharePhotometry: bool | None = Field(
        default=None,
        description="Boolean indicating whether user can share photometry points "
        "to other groups. Either this, `admin` or `canSave` must be provided in "
        "request body.",
    )


class GroupUsersFromGroupsPostBody(BaseModel):
    """Request body for adding users from other group(s)."""

    model_config = ConfigDict(extra="forbid")

    fromGroupIDs: list[int] | None = Field(
        default=None, description="IDs of the groups to add users from."
    )


class GroupStreamPostBody(BaseModel):
    """Request body for adding an alert stream to a group."""

    model_config = ConfigDict(extra="forbid")

    stream_id: int | None = Field(
        default=None, description="ID of the stream to add to the group."
    )


class GroupStreamPostResponse(BaseModel):
    """Data payload returned when adding a stream to a group."""

    group_id: int = Field(description="Group ID")
    stream_id: int = Field(description="Stream ID")


__all__ = [
    "GroupGetQuery",
    "GroupPostBody",
    "GroupPostResponse",
    "GroupPutBody",
    "GroupUserPostBody",
    "GroupUserPostResponse",
    "GroupUserPatchBody",
    "GroupUsersFromGroupsPostBody",
    "GroupStreamPostBody",
    "GroupStreamPostResponse",
    "GroupPost",
    "GroupMemberResponse",
    "GroupResponse",
    "GroupUserResponse",
    "GroupsResponse",
]
