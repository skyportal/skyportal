"""Response models for ``/api/{resource_type}/{id}/reminders``."""

from __future__ import annotations

from datetime import date

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


class ReminderPostBody(BaseModel):
    """Request body for creating reminder(s)."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(description="Text to post for the reminder")
    next_reminder: str = Field(
        description="Arrow-parseable date string for the next reminder"
    )
    reminder_delay: float = Field(
        default=1, description="Delay until the next reminder in days"
    )
    number_of_reminders: int = Field(
        default=1, description="Number of remaining reminders"
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view reminder. Defaults to all of requesting user's groups.",
    )
    user_ids: list[int] | None = Field(
        default=None,
        description="List of IDs of users to post the reminder for. Defaults to "
        "the requesting user.",
    )


class ReminderPostResponse(BaseModel):
    """IDs of the newly created reminders."""

    reminder_ids: list[int] = Field(
        description="IDs of the new reminders (one per user)"
    )


class ReminderPatchBody(BaseModel):
    """Request body for updating a reminder."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = Field(default=None, description="Text to post for the reminder")
    next_reminder: str | None = Field(
        default=None, description="Arrow-parseable date string for the next reminder"
    )
    reminder_delay: float | None = Field(
        default=None, description="Delay until the next reminder in days"
    )
    number_of_reminders: int | None = Field(
        default=None, description="Number of remaining reminders"
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view reminder. Left unchanged if not provided.",
    )


__all__ = [
    "ReminderPostBody",
    "ReminderPostResponse",
    "ReminderPatchBody",
    "ReminderPost",
    "ReminderUpdate",
    "ReminderResponse",
    "RemindersResponse",
]
