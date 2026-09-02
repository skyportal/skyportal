"""Response models for ``/api/earthquake``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.comments import CommentResponse
from skyportal_py_models.reminders import ReminderResponse
from skyportal_py_models.users import UserResponse


class EarthquakeNoticeResponse(BaseModel):
    """A single notice about an earthquake.

    ``content`` is the raw QuakeML document, a deferred ``LargeBinary`` column,
    so it is only present on the single-event endpoint (which undefers it).
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    sent_by: UserResponse | None = None
    content: Any = None
    event_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    depth: float | None = None
    magnitude: float | None = None
    date: datetime | None = None
    country: str | None = None


class EarthquakePredictionResponse(BaseModel):
    """A predicted seismic arrival."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    event_id: int | None = None
    detector_id: int | None = None
    d: float | None = None
    p: datetime | None = None
    s: datetime | None = None
    r2p0: datetime | None = None
    r3p5: datetime | None = None
    r5p0: datetime | None = None
    rfamp: float | None = None
    lockloss: float | None = None


class EarthquakeMeasurementResponse(BaseModel):
    """A measured ground velocity (an ``EarthquakeMeasured`` row)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    event_id: int | None = None
    detector_id: int | None = None
    rfamp: float | None = None
    lockloss: int | None = None


class EarthquakeResponse(BaseModel):
    """An earthquake event.

    The single-event endpoint replaces ``comments`` with hand-built dicts that
    drop ``attachment_bytes`` and add ``author`` and ``resourceType``.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    sent_by: UserResponse | None = None
    event_id: str | None = None
    event_uri: str | None = None
    status: str | None = None
    notices: list[EarthquakeNoticeResponse] = Field(default_factory=list)
    predictions: list[EarthquakePredictionResponse] = Field(default_factory=list)
    measurements: list[EarthquakeMeasurementResponse] = Field(default_factory=list)
    comments: list[CommentResponse] = Field(default_factory=list)
    reminders: list[ReminderResponse] = Field(default_factory=list)


class EarthquakesPageResponse(BaseModel):
    """One page of results from an earthquake events query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    events: list[EarthquakeResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)


class EarthquakePost(BaseModel):
    """Payload for ingesting an earthquake event."""

    model_config = ConfigDict(extra="forbid")

    xml: str | None = None
    event_id: str | None = None
    date: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    depth: float | None = None
    magnitude: float | None = None


class EarthquakePostBody(BaseModel):
    """Request body for ingesting an earthquake event, either from a QuakeML
    xml document or from explicit event properties."""

    model_config = ConfigDict(extra="forbid")

    xml: str | None = Field(
        default=None, description="QuakeML xml document describing the event"
    )
    event_id: str | None = Field(
        default=None, description="Earthquake event ID; required if xml is not given"
    )
    date: str | None = Field(
        default=None,
        description="Date of the event; required if xml is not given",
    )
    latitude: float | None = Field(
        default=None, description="Event latitude [deg]; required if xml is not given"
    )
    longitude: float | None = Field(
        default=None, description="Event longitude [deg]; required if xml is not given"
    )
    depth: float | None = Field(
        default=None, description="Event depth [m]; required if xml is not given"
    )
    magnitude: float | None = Field(
        default=None, description="Event magnitude; required if xml is not given"
    )


class EarthquakePostResponse(BaseModel):
    """ID of the ingested earthquake event."""

    id: str | int | None = Field(description="Earthquake event ID")


class EarthquakeMeasurementBody(BaseModel):
    """Request body for posting or updating a ground velocity measurement;
    at least one of rfamp or lockloss must be provided."""

    model_config = ConfigDict(extra="forbid")

    rfamp: float | None = Field(
        default=None, description="Earthquake amplitude measured [m/s]"
    )
    lockloss: int | None = Field(
        default=None,
        description="Earthquake lockloss measured, 0 (no lockloss) or 1 (lockloss)",
    )


class EarthquakeGetQuery(BaseModel):
    """Query parameters for retrieving Earthquake events."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "date >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "date <= endDate"
        ),
    )
    statusKeep: str | None = Field(
        default=None,
        description="Earthquake Status to match against",
    )
    statusRemove: str | None = Field(
        default=None,
        description="Earthquake Status to filter out",
    )
    numPerPage: int = Field(
        default=100,
        description="Number of earthquakes. Defaults to 100.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for iterating through all earthquakes. Defaults to 1",
    )
