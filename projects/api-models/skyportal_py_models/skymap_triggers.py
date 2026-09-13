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
