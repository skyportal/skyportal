"""Response models for ``/api/skymap_trigger``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SkymapTriggerQueueResponse(BaseModel):
    """The skymap-based triggers currently queued on a remote facility.

    The names come straight back from the instrument's remote observation
    plan API, so there is no corresponding database model.
    """

    model_config = ConfigDict(extra="forbid")

    trigger_names: list[str] = Field(default_factory=list)


class SkymapTriggerPostBody(BaseModel):
    """Request body for posting a skymap-based trigger."""

    model_config = ConfigDict(extra="forbid")

    allocation_id: int = Field(description="Followup request allocation ID.")
    localization_id: int = Field(description="Localization ID.")
    integrated_probability: float = Field(
        default=0.95, description="Integrated probability within skymap."
    )


class SkymapTriggerDeleteBody(BaseModel):
    """Request body for deleting a skymap-based trigger."""

    model_config = ConfigDict(extra="forbid")

    trigger_name: str | None = Field(
        default=None, description="Name of the trigger/queue to remove"
    )
