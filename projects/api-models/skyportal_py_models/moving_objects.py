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


__all__ = [
    "MovingObjectFollowupPost",
    "MovingObjectFollowupPostBody",
    "MovingObjectObservationResponse",
]


class TrackDetection(BaseModel):
    """One detection in a linked track, as the linker reports it."""

    model_config = ConfigDict(extra="forbid")

    candid: str | int = Field(description="Alert id the cutouts are keyed on.")
    jd: float = Field(description="Julian date of the detection.")
    ra: float = Field(description="Right ascension in degrees.")
    dec: float = Field(description="Declination in degrees.")
    mag: float | None = Field(default=None, description="Reported magnitude.")
    band: str | None = Field(default=None, description="Filter the detection is in.")


class MovingObjectTrackPostBody(BaseModel):
    """Request body for measuring a linked track from its cutouts."""

    model_config = ConfigDict(extra="forbid")

    detections: list[TrackDetection] = Field(
        description="The track's detections. Not keyed on obj_id: a moving "
        "object gets a new one almost every epoch, which is the whole problem."
    )
    broker_id: int = Field(description="Broker to fetch the cutouts from.")
    survey: str = Field(default="ZTF", description="Survey the alerts are from.")
    cutout: str = Field(
        default="cutoutDifference",
        description="Which cutout to measure. Only the difference image is "
        "meaningful for a moving object.",
    )
    include_images: bool = Field(
        default=True,
        description="Render each epoch as a PNG stretched to its own "
        "background. Off returns the numbers alone.",
    )
    check_known: bool = Field(
        default=False,
        description="Ask JPL whether the track is an already-known small body. "
        "Costs a few queries, and reports a negative only when a control "
        "observation proves the query path still works.",
    )
    measure_cutouts: bool = Field(
        default=True,
        description="Measure each epoch's pixels. Off returns the geometry "
        "alone, which needs no cutouts and so no broker call: a scanning page "
        "can show it for every candidate, where measuring cannot.",
    )
