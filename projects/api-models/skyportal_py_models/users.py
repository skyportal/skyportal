"""Response models for ``/api/user``."""

from __future__ import annotations

from datetime import date
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import UserResponse
from skyportal_py_models.notifications import email


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


class UserPostBody(BaseModel):
    """Request body for adding a new user."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(description="Username of the new user")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    affiliations: list[str] | None = Field(
        default=None, description="User's list of affiliations"
    )
    contact_email: str | None = Field(
        default=None, description="User's contact email address"
    )
    contact_phone: str | None = Field(
        default=None, description="User's contact phone number"
    )
    oauth_uid: str | None = Field(default=None, description="User's OAuth UID")
    roles: list[str] = Field(
        default_factory=list,
        description="List of user roles. Defaults to `[Full user]`. Will be "
        "overridden by `groupIDsAndAdmin` on a per-group basis.",
    )
    groupIDsAndAdmin: list[tuple[int, bool]] = Field(
        default_factory=list,
        description="Array of 2-element arrays `[groupID, admin]` where `groupID` "
        "is the ID of a group that the new user will be added to and `admin` is "
        "a boolean indicating whether they will be an admin in that group, "
        "e.g. `[[group_id_1, true], [group_id_2, false]]`",
    )


class UserPostResponse(BaseModel):
    """ID of the newly added user."""

    id: int = Field(description="New user ID")


class UserPatchBody(BaseModel):
    """Request body for updating a user."""

    model_config = ConfigDict(extra="forbid")

    expirationDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). Set a "
        "user's expiration date, after which the user's account will be "
        "deactivated and will be unable to access the application. An explicit "
        "null or empty string clears the expiration date.",
    )
    username: str | None = Field(default=None, description="New username")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    contact_email: str | None = Field(
        default=None, description="User's contact email address"
    )


class UserGetQuery(BaseModel):
    """Query parameters for listing users."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    numPerPage: int | None = Field(
        default=None,
        description="Number of users to return per paginated request. Defaults to all users.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    firstName: str | None = Field(
        default=None,
        description="Get users whose first name contains this string.",
    )
    lastName: str | None = Field(
        default=None,
        description="Get users whose last name contains this string.",
    )
    username: str | None = Field(
        default=None,
        description="Get users whose username contains this string.",
    )
    email: str | None = Field(
        default=None,
        description="Get users whose email contains this string.",
    )
    role: str | None = Field(
        default=None,
        description="Get users with the role.",
    )
    acl: str | None = Field(
        default=None,
        description="Get users with this ACL.",
    )
    group: str | None = Field(
        default=None,
        description="Get users part of the group with name given by this parameter.",
    )
    stream: str | None = Field(
        default=None,
        description="Get users with access to the stream with name given by this parameter.",
    )
    slim: bool = Field(
        default=False,
        description=(
            "Return only what is needed to name a user (id, username, first "
            "and last name, is_bot). Callers that just label a comment, a "
            "redshift or an assignment do not need each user's groups, roles "
            "and ACLs, which are most of the response."
        ),
    )
    includeExpired: bool = Field(
        default=False,
        description="Include users with expired accounts in the results.",
    )
    sortBy: Literal["username", "createdAt"] = Field(
        default="username",
        description="Field to sort by. Options are 'username' (alphabetical, default) or 'createdAt' (creation date).",
    )
    sortOrder: Literal["asc", "desc"] = Field(
        default="asc",
        description="Sort order - 'asc' for ascending (default) or 'desc' for descending.",
    )


__all__ = [
    "UserPostBody",
    "UserPostResponse",
    "UserPatchBody",
    "UserGetQuery",
    "UserPost",
    "UserResponse",
    "UsersPageResponse",
]
