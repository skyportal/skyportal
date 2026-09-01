"""Response models for ``/api/invitations``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse
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
