"""Response models for ``/api/moving_object``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MovingObjectObservationResponse(BaseModel):
    """A scheduled exposure from ``find_observable_sequence``.

    This is not a database model: the handler returns the plain dicts built
    by ``skyportal.utils.moving_objects.find_observable_sequence``, nothing is
    persisted, and the keys below are the complete set.
    """

    model_config = ConfigDict(extra="forbid")

    start_time: datetime | None = None
    end_time: datetime | None = None
    band: str | None = None
    field_id: int | None = None
    airmass: float | None = None
    sun_altitude: float | None = None
    moon_distance: float | None = None
