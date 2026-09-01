"""Response models for ``/api/mmadetector``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MMADetectorSpectrumResponse(BaseModel):
    """A sensitivity spectrum of a detector.

    ``owner`` and ``groups`` stay untyped: the user and group models both own
    an ``mmadetector_spectra`` relationship, so typing them here would risk an
    import cycle.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    detector_id: int | None = None
    detector: MMADetectorResponse | None = None
    frequencies: list[float] = Field(default_factory=list)
    amplitudes: list[float] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    owner_id: int | None = None
    owner: dict[str, Any] | None = None
    groups: list[dict[str, Any]] | None = None
    original_file_string: str | None = None
    original_file_filename: str | None = None


class MMADetectorTimeIntervalResponse(BaseModel):
    """A detector data-taking interval.

    The time-interval endpoints build this payload by hand, so it carries only
    these five keys rather than the model's full column set. ``owner`` and
    ``groups`` stay untyped: the user and group models both own an
    ``mmadetector_time_intervals`` relationship, so typing them here would
    risk an import cycle.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    time_interval: list[datetime] = Field(default_factory=list)
    owner: dict[str, Any] | None = None
    groups: list[dict[str, Any]] | None = None
    detector: MMADetectorResponse | None = None


class MMADetectorResponse(BaseModel):
    """A multimessenger astronomical detector.

    ``events`` stays untyped: the GCN event model points back at
    ``MMADetector``, so typing it would create an import cycle.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    nickname: str | None = None
    aliases: list[str] | None = None
    type: (
        Literal["gravitational-wave", "neutrino", "gamma-ray-burst", "x-ray"] | None
    ) = None
    lat: float | None = None
    lon: float | None = None
    elevation: float | None = None
    fixed_location: bool | None = None
    events: list[dict[str, Any]] | None = None
    spectra: list[MMADetectorSpectrumResponse] | None = None
    time_intervals: list[MMADetectorTimeIntervalResponse] | None = None


class MMADetectorTimeIntervalsPostResponse(BaseModel):
    """Result of uploading MMA detector time intervals."""

    model_config = ConfigDict(extra="forbid")

    ids: list[int] = Field(default_factory=list)


MMADetectorResponse.model_rebuild()

MMADetectorSpectrumResponse.model_rebuild()

MMADetectorTimeIntervalResponse.model_rebuild()


class MMADetectorPost(BaseModel):
    """Payload for creating an MMA detector."""

    model_config = ConfigDict(extra="forbid")

    name: str
    nickname: str
    type: str
    fixed_location: bool
    lat: float | None = None
    lon: float | None = None
    elevation: float | None = None


class MMADetectorSpectrumPost(BaseModel):
    """Payload for uploading an MMA detector spectrum."""

    model_config = ConfigDict(extra="forbid")

    frequencies: list[float]
    amplitudes: list[float]
    start_time: str
    end_time: str
    detector_id: int
    group_ids: list[int] | str | None = None
