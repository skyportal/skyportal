"""Response models for ``/api/observation``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.instruments import InstrumentFieldResponse, InstrumentResponse


class ObservationResponse(BaseModel):
    """A survey observation, either executed or queued.

    The endpoint returns either kind depending on ``observationStatus``, so
    the executed-only fields (``observation_id``, ``airmass``, ``seeing``,
    ``limmag``, ``target_name``, ``processed_fraction``) and the queued-only
    ones (``queue_name``, ``validity_window_start``, ``validity_window_end``)
    are all optional.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    instrument_id: int | None = None
    instrument_field_id: int | None = None
    observation_id: int | None = None
    obstime: datetime | None = None
    filt: str | None = None
    exposure_time: int | None = None
    airmass: float | None = None
    seeing: float | None = None
    limmag: float | None = None
    target_name: str | None = None
    processed_fraction: float | None = None
    queue_name: str | None = None
    validity_window_start: datetime | None = None
    validity_window_end: datetime | None = None
    field: InstrumentFieldResponse | None = None
    instrument: InstrumentResponse | None = None


class ObservationsPageResponse(BaseModel):
    """One page of results from an observations query.

    The statistics and GeoJSON keys are only present when the request asked
    for them.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    observations: list[ObservationResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)
    probability: float | None = None
    area: float | None = None
    geojson: list[dict[str, Any]] | None = None
    field_ids: list[int] | None = None
    min_observations_per_field: int | None = None


class ObservationQueuesResponse(BaseModel):
    """Queue names retrieved from an instrument's external API."""

    model_config = ConfigDict(extra="forbid")

    queue_names: list[str] = Field(default_factory=list)


class ObservationSimSurveyResponse(BaseModel):
    """Result of starting a SimSurvey efficiency calculation."""

    model_config = ConfigDict(extra="forbid")

    id: int
