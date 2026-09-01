"""Response models for ``/api/internal/profile``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.group_admission_requests import GroupAdmissionRequestResponse
from skyportal_py_models.streams import StreamResponse


class ProfileTokenResponse(BaseModel):
    """An API token of the profile's user (baselayer ``Token``)."""

    # Hand-built by the profile handler, so it carries only these four keys.

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: str | None = None
    acls: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class UserProfileResponse(BaseModel):
    """The user associated with the API token (baselayer ``User``)."""

    # The handler builds this dict by hand: ``User.to_dict()`` (the table
    # columns except ``preferences``) plus the keys it injects.

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    id: int | None = None
    created_at: datetime | None = None
    modified: datetime | None = None
    username: str
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    affiliations: list[str] = Field(default_factory=list)
    contact_email: str | None = None
    contact_phone: str | None = None
    oauth_uid: str | None = None
    is_bot: bool | None = None
    expiration_date: datetime | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    acls: list[str] = Field(default_factory=list)
    tokens: list[ProfileTokenResponse] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    gravatar_url: str | None = None
    group_admission_requests: list[GroupAdmissionRequestResponse] = Field(
        alias="groupAdmissionRequests", default_factory=list
    )
    streams: list[StreamResponse] = Field(default_factory=list)
    is_anonymous: bool | None = None


class ProfilePatch(BaseModel):
    """Payload for updating the token user's profile and preferences."""

    model_config = ConfigDict(extra="forbid")

    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    affiliations: list[str] | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    bio: str | None = None
    is_bot: bool | None = None
    preferences: dict[str, Any] | None = None
