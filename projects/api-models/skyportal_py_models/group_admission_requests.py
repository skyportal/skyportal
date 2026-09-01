"""Response models for ``/api/group_admission_requests``."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.users import UserResponse


class GroupAdmissionRequestResponse(BaseModel):
    """A request to join a group."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    user_id: int | None = None
    group_id: int | None = None
    status: Literal["pending", "accepted", "declined"] | None = None
    user: UserResponse | None = None
    group: GroupResponse | None = None


class GroupAdmissionRequestGetQuery(BaseModel):
    """Query parameters for listing group admission requests."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    groupID: int | None = Field(
        default=None,
        description="ID of group for which admission requests are desired",
    )


class GroupAdmissionRequestPostBody(BaseModel):
    """Request body for creating a group admission request."""

    model_config = ConfigDict(extra="forbid")

    groupID: int = Field(description="ID of the group to request admission to")
    userID: int = Field(description="ID of the user requesting admission")


class GroupAdmissionRequestPostResponse(BaseModel):
    """Data payload returned when creating a group admission request."""

    id: int = Field(description="New group admission request ID")


class GroupAdmissionRequestPatchBody(BaseModel):
    """Request body for updating a group admission request's status."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["pending", "accepted", "declined"] = Field(
        description="One of either 'accepted', 'declined', or 'pending'."
    )
