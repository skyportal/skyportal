"""Response models for ``/api/weather``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WeatherResponse(BaseModel):
    """Cached OpenWeather data for a telescope site.

    The handler builds this dict by hand: ``weather`` is the raw OpenWeather
    ``weather_info`` JSON blob, ``weather_retrieved_at`` is the Weather row's
    ``retrieved_at``, and the remaining keys come off the associated Telescope.
    """

    model_config = ConfigDict(extra="forbid")

    weather: dict[str, Any] | None = None
    weather_retrieved_at: datetime | None = None
    weather_fetch_at: datetime | None = None
    weather_link: str | None = None
    telescope_name: str | None = None
    telescope_nickname: str | None = None
    telescope_id: int | None = None
    message: str | None = None


class WeatherGetQuery(BaseModel):
    """Query parameters for retrieving weather at a telescope site."""

    model_config = ConfigDict(extra="forbid")

    telescope_id: int | None = Field(
        default=None,
        description="ID of the telescope to report weather for. If not given, "
        "the telescope saved in the user's preferences is used.",
    )
