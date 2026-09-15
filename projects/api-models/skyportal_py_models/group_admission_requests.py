"""Response models for ``/api/group_admission_requests``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
