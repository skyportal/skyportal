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


__all__ = [
    "ReminderResponse",
    "RemindersResponse",
]
