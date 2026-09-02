"""Response models for ``/api/moving_object``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class MovingObjectFollowupPost(BaseModel):
    """Payload for scheduling follow-up of a moving object."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    instrument_id: int
    exposure_count: int
    exposure_time: float
    start_time: str
    end_time: str
    band: str = Field(alias="filter")
    primary_only: bool | None = None
    airmass_limit: float | None = None
    moon_distance_limit: float | None = None
    sun_altitude_limit: float | None = None
    references_only: bool | None = None


class MovingObjectFollowupPostBody(BaseModel):
    """Request body for a moving object follow-up observation plan."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: int | None = Field(
        default=None, description="ID of the instrument to use"
    )
    exposure_count: int | None = Field(default=None, description="Number of exposures")
    exposure_time: float | None = Field(
        default=None, description="Exposure time in seconds"
    )
    start_time: str | None = Field(
        default=None, description="Start time of the obversations' time window"
    )
    end_time: str | None = Field(
        default=None, description="End time of the obversations' time window"
    )
    filter: str | None = Field(default=None, description="Filter to use")
    primary_only: bool = Field(
        default=True,
        description="Only consider an instrument's fields from it's primary grid, if any",
    )
    airmass_limit: float = Field(
        default=2.5, description="Maximum airmass for observations. Default is 2.5"
    )
    moon_distance_limit: float = Field(
        default=30,
        description="Minimum distance from the Moon in degrees. Default is 30",
    )
    sun_altitude_limit: float = Field(
        default=-18,
        description="Maximum altitude of the Sun in degrees. Default is -18",
    )
    references_only: bool = Field(
        default=False,
        description="Only consider fields that have reference images available",
    )
