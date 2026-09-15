"""Response models for ``/api/shifts``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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
