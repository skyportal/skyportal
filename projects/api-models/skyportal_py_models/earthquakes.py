"""Response models for ``/api/earthquake``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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
