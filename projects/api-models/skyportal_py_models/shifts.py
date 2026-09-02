"""Response models for ``/api/shifts``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.users import UserResponse


class ShiftUserMembershipResponse(BaseModel):
    """A user's membership in a shift (the ``ShiftUser`` join model).

    ``username``, ``first_name`` and ``last_name`` are copied up from the
    nested ``user`` by the single-shift handler.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    shift_id: int | None = None
    user_id: int | None = None
    admin: bool | None = None
    needs_replacement: bool | None = None
    user: UserResponse | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class ShiftCommentAuthorResponse(UserResponse):
    """A shift comment's author, with the gravatar URL the handler adds."""

    gravatar_url: str | None = None


class ShiftCommentResponse(BaseModel):
    """A comment posted about a shift (the ``CommentOnShift`` model).

    The handler strips ``attachment_bytes`` and tags each comment with
    ``resourceType``.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    text: str | None = None
    attachment_name: str | None = None
    origin: str | None = None
    bot: bool | None = None
    author_id: int | None = None
    shift_id: int | None = None
    author: ShiftCommentAuthorResponse | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    resource_type: str | None = Field(alias="resourceType", default=None)


class ShiftGroupMemberResponse(BaseModel):
    """A member of a shift's group, as returned alongside a single shift."""

    model_config = ConfigDict(extra="forbid")

    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    expiration_date: datetime | None = None


class ShiftGroupResponse(BaseModel):
    """A shift's group, as hand-assembled by the single-shift handler."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str | None = None
    has_admin_access: bool | None = None
    group_users: list[ShiftGroupMemberResponse] = Field(default_factory=list)


class ShiftResponse(BaseModel):
    """A group scanning shift.

    ``shift_users_ids`` is a column property (an aggregate of the shift's
    user IDs), so it is present even when no relationship is loaded.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    description: str | None = None
    start_date: datetime
    end_date: datetime
    group_id: int
    required_users_number: int | None = None
    shift_users_ids: list[int] | None = None
    shift_users: list[ShiftUserMembershipResponse] = Field(default_factory=list)
    users: list[UserResponse] = Field(default_factory=list)
    comments: list[ShiftCommentResponse] = Field(default_factory=list)
    # typed as dict to avoid an import cycle with reminders
    reminders: list[dict[str, Any]] = Field(default_factory=list)
    group: ShiftGroupResponse | None = None


class ShiftSummarySectionResponse(BaseModel):
    """One section (shifts or GCN events) of a shift summary report."""

    model_config = ConfigDict(extra="forbid")

    total: int | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)


class ShiftSummaryReportResponse(BaseModel):
    """Summary of shift-user activity over a period."""

    model_config = ConfigDict(extra="forbid")

    shifts: ShiftSummarySectionResponse | None = None
    gcns: ShiftSummarySectionResponse | None = None


class ShiftPost(BaseModel):
    """Payload for creating a new shift."""

    model_config = ConfigDict(extra="forbid")

    name: str
    start_date: str
    end_date: str
    group_id: int
    description: str | None = None
    required_users_number: int | None = None
    shift_admins: list[int] | None = None


class ShiftGetQuery(BaseModel):
    """Query parameters for retrieving shifts."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    group_id: int | None = Field(
        default=None,
        description="Filter shifts by group ID",
    )
    start_date_limit: str | None = Field(
        default=None,
        description="Arrow-parseable date string. Return shifts that start after or at this datetime",
    )
    end_date_limit: str | None = Field(
        default=None,
        description="Arrow-parseable date string. Return shifts that end after or at this datetime",
    )


class ShiftPostBody(BaseModel):
    """Request body for creating a shift."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Name of the shift.")
    group_id: int = Field(description="ID of the Shift's Group.")
    start_date: str = Field(description="The start time of this shift.")
    end_date: str = Field(description="The end time of this shift.")
    description: str | None = Field(
        default=None, description="Longer description of the shift."
    )
    required_users_number: int | None = Field(
        default=None,
        description="The number of users required to join this shift for it to "
        "be considered full.",
    )
    shift_admins: list[int] | None = Field(
        default=None, description="List of IDs of users to be shift admins."
    )


class ShiftPostResponse(BaseModel):
    """Data payload returned when creating a shift."""

    id: int = Field(description="New Shift ID")


class ShiftPatchBody(BaseModel):
    """Request body for updating a shift."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Name of the shift.")
    description: str | None = Field(
        default=None, description="Longer description of the shift."
    )
    required_users_number: int | None = Field(
        default=None,
        description="The number of users required to join this shift for it to "
        "be considered full.",
    )


class ShiftUserPostBody(BaseModel):
    """Request body for adding a user to a shift."""

    model_config = ConfigDict(extra="forbid")

    userID: int = Field(description="ID of the user to add to the shift.")
    admin: bool = Field(
        default=False,
        description="Boolean indicating whether user is shift admin.",
    )
    needs_replacement: bool = Field(
        default=False,
        description="Boolean indicating whether user needs replacement or not.",
    )


class ShiftUserPostResponse(BaseModel):
    """Data payload returned when adding a user to a shift."""

    shift_id: int = Field(description="Shift ID")
    user_id: int = Field(description="User ID")
    admin: bool = Field(description="Boolean indicating whether user is shift admin")


class ShiftUserPatchBody(BaseModel):
    """Request body for updating a shift user."""

    model_config = ConfigDict(extra="forbid")

    admin: bool | None = Field(
        default=None,
        description="Boolean indicating whether user is shift admin.",
    )
    needs_replacement: bool | None = Field(
        default=None,
        description="Boolean indicating whether user needs replacement or not.",
    )


class ShiftSummaryGetQuery(BaseModel):
    """Query parameters for summarizing shift activity."""

    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "shift.start_date >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "shift.start_date <= endDate"
        ),
    )
