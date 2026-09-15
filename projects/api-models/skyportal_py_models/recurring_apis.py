"""Response models for ``/api/recurring_api``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from skyportal_py_models.users import UserResponse


class RecurringAPIResponse(BaseModel):
    """A recurring API call scheduled by a user.

    ``owner`` is always loaded. The multiple-object endpoint decodes
    ``payload`` from its stored JSON string, while the single-object one
    returns it exactly as stored.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    endpoint: str | None = None
    method: str | None = None
    payload: dict[str, Any] | str | None = None
    next_call: datetime | None = None
    call_delay: float | None = None
    number_of_retries: int | None = None
    active: bool | None = None
    owner_id: int | None = None
    owner: UserResponse | None = None
