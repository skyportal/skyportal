"""Response models for ``/api/{resource_type}/{id}/reminders``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import ReminderResponse


class RemindersResponse(BaseModel):
    """All reminders attached to one resource."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    resource_id: str = Field(alias="resourceId")
    resource_type: str = Field(alias="resourceType")
    reminders: list[ReminderResponse] = Field(default_factory=list)


class ReminderPost(BaseModel):
    """Payload for creating reminders on a resource."""

    model_config = ConfigDict(extra="forbid")

    text: str
    next_reminder: str
    reminder_delay: float | None = None
    number_of_reminders: int | None = None
    group_ids: list[int] | None = None
    user_ids: list[int] | None = None


class ReminderUpdate(BaseModel):
    """Payload for updating an existing reminder."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    origin: str | None = None
    bot: bool | None = None
    next_reminder: str | None = None
    reminder_delay: float | None = None
    number_of_reminders: int | None = None
    group_ids: list[int] | None = None
    user_ids: list[int] | None = None


__all__ = [
    "ReminderPost",
    "ReminderUpdate",
    "ReminderResponse",
    "RemindersResponse",
]
