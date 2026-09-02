"""Response models for ``/api/invitations``."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.notifications import email
from skyportal_py_models.roles import RoleResponse
from skyportal_py_models.streams import StreamResponse
from skyportal_py_models.users import UserResponse


class InvitationResponse(BaseModel):
    """An invitation for a new user to join the instance."""

    # The handler eager-loads ``groups``, ``streams`` and ``invited_by``;
    # ``role`` is only present when that relationship happens to be loaded.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    token: str | None = None
    user_email: str | None = None
    role_id: str | None = None
    role: RoleResponse | None = None
    admin_for_groups: list[bool] | None = None
    can_save_to_groups: list[bool] | None = None
    can_share_photometry_for_groups: list[bool] | None = None
    used: bool | None = None
    user_expiration_date: datetime | None = None
    groups: list[GroupResponse] | None = None
    streams: list[StreamResponse] | None = None
    invited_by: UserResponse | None = None


class InvitationsPageResponse(BaseModel):
    """One page of results from an invitations query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    invitations: list[InvitationResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)


class InvitationPost(BaseModel):
    """Payload for inviting a new user."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    user_email: str = Field(alias="userEmail")
    group_ids: list[int] = Field(alias="groupIDs")
    role: str | None = None
    stream_ids: list[int] | None = Field(alias="streamIDs", default=None)
    group_admin: list[bool] | None = Field(alias="groupAdmin", default=None)
    can_save: list[bool] | None = Field(alias="canSave", default=None)
    can_share_photometry: list[bool] | None = Field(
        alias="canSharePhotometry", default=None
    )
    user_expiration_date: str | None = Field(alias="userExpirationDate", default=None)


class InvitationGetQuery(BaseModel):
    """Query parameters for listing invitations."""

    model_config = ConfigDict(extra="forbid")

    includeUsed: bool = Field(
        default=False,
        description="Bool indicating whether to include used invitations. Defaults to false.",
    )
    numPerPage: int = Field(
        default=25,
        description="Number of invitations to return per paginated request. Defaults to 25.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    email: str | None = Field(
        default=None,
        description="Get invitations whose email contains this string.",
    )
    group: str | None = Field(
        default=None,
        description="Get invitations part of the group with name given by this parameter.",
    )
    stream: str | None = Field(
        default=None,
        description="Get invitations with access to the stream with name given by this parameter.",
    )
    invitedBy: str | None = Field(
        default=None,
        description="Get invitations invited by users whose username contains this string.",
    )


class InvitationPostBody(BaseModel):
    """Request body for inviting a new user."""

    model_config = ConfigDict(extra="forbid")

    userEmail: str = Field(description="Email address to send the invitation to.")
    groupIDs: list[int] = Field(
        description="List of IDs of groups invited user will be added to. If "
        "`streamIDs` is not provided, invited user will be given accesss to "
        "all streams associated with the groups specified by this field."
    )
    role: str = Field(
        default="Full user",
        description="The role the new user will have in the system. "
        'If provided, must be one of either "Full user" or "View only". '
        'Defaults to "Full user".',
    )
    streamIDs: list[int] | None = Field(
        default=None,
        description="List of IDs of streams invited user will be given access "
        "to. If not provided, user will be granted access to all streams "
        "associated with the groups specified by `groupIDs`.",
    )
    groupAdmin: list[bool] | None = Field(
        default=None,
        description="List of booleans indicating whether user should be "
        "granted admin status for respective specified group(s). Defaults to "
        "all false.",
    )
    canSave: list[bool] | None = Field(
        default=None,
        description="List of booleans indicating whether user should be able "
        "to save sources to respective specified group(s). Defaults to all "
        "true.",
    )
    canSharePhotometry: list[bool] | None = Field(
        default=None,
        description="List of booleans indicating whether user should be able "
        "to share photometry points to respective specified group(s). Defaults to all "
        "false.",
    )
    userExpirationDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). Set a "
        "user's expiration date, after which the user's account will be "
        "deactivated and will be unable to access the application.",
    )


class InvitationPostResponse(BaseModel):
    """Data payload returned when creating an invitation."""

    id: int = Field(description="New invitation ID")


class InvitationPatchBody(BaseModel):
    """Request body for updating a pending invitation."""

    model_config = ConfigDict(extra="forbid")

    groupIDs: list[int] | None = Field(
        default=None, description="List of IDs of groups the user is invited to."
    )
    streamIDs: list[int] | None = Field(
        default=None,
        description="List of IDs of streams invited user will be given access to.",
    )
    role: str | None = Field(
        default=None, description="The role the new user will have in the system."
    )
    userExpirationDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). Set a "
        "user's expiration date, after which the user's account will be "
        "deactivated and will be unable to access the application.",
    )
