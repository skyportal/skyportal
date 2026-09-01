"""Response models for ``/api/recurring_api``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


class RecurringAPIPost(BaseModel):
    """Payload for scheduling a recurring API call."""

    model_config = ConfigDict(extra="forbid")

    endpoint: str
    method: str
    next_call: str
    call_delay: float
    payload: str
    number_of_retries: int | None = None


MAX_RETRIES = 10


class RecurringAPIPostBody(BaseModel):
    """Request body for creating a recurring API."""

    model_config = ConfigDict(extra="forbid")

    endpoint: str = Field(description="Endpoint of the API call.")
    method: str = Field(description="HTTP method of the API call.")
    next_call: str = Field(description="Time of the next API call.")
    call_delay: float = Field(gt=0, description="Delay until next API call in days.")
    payload: str = Field(description="JSON string with the payload of the API call.")
    number_of_retries: int | None = Field(
        default=None,
        ge=1,
        le=MAX_RETRIES,
        description="Number of retries before service is deactivated.",
    )


class RecurringAPIPostResponse(BaseModel):
    """Data payload returned when creating a recurring API."""

    id: int = Field(description="New RecurringAPI ID")
