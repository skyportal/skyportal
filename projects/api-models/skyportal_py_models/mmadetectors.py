"""Response models for ``/api/mmadetector``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

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


class MMADetectorGetQuery(BaseModel):
    """Query parameters for listing MMA Detectors."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    name: str | None = Field(
        default=None,
        description="Filter by name",
    )


class MMADetectorPostBody(BaseModel):
    """Request body for creating an MMADetector."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Unabbreviated facility name (e.g., LIGO Hanford Observatory)."
    )
    nickname: str = Field(description="Abbreviated facility name (e.g., H1).")
    aliases: list[str] | None = Field(
        default=None,
        description="Other names GCN notices use for this detector (e.g. Fermi "
        "for FermiGBM). An event is linked when a tag matches the nickname or "
        "any alias.",
    )
    type: str = Field(
        description="MMA detector type, one of gravitational-wave, neutrino, "
        "gamma-ray-burst, or x-ray."
    )
    lat: float | None = Field(default=None, description="Latitude in deg.")
    lon: float | None = Field(default=None, description="Longitude in deg.")
    elevation: float | None = Field(default=None, description="Elevation in meters.")
    fixed_location: bool | None = Field(
        default=None,
        description="Does this detector have a fixed location (lon, lat, elev)?",
    )


class MMADetectorPostResponse(BaseModel):
    """Data payload returned when creating an MMADetector."""

    id: int = Field(description="New mmadetector ID")


class MMADetectorPatchBody(BaseModel):
    """Request body for updating an MMADetector."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Unabbreviated facility name.")
    nickname: str | None = Field(default=None, description="Abbreviated facility name.")
    aliases: list[str] | None = Field(
        default=None,
        description="Other names GCN notices use for this detector.",
    )
    type: str | None = Field(default=None, description="MMA detector type.")
    lat: float | None = Field(default=None, description="Latitude in deg.")
    lon: float | None = Field(default=None, description="Longitude in deg.")
    elevation: float | None = Field(default=None, description="Elevation in meters.")
    fixed_location: bool | None = Field(
        default=None,
        description="Does this detector have a fixed location (lon, lat, elev)?",
    )


class MMADetectorSpectrumPostBody(BaseModel):
    """Request body for uploading an MMADetector spectrum."""

    model_config = ConfigDict(extra="forbid")

    frequencies: list[float] = Field(description="Frequencies of the spectrum [Hz].")
    amplitudes: list[float] = Field(
        description="Amplitude of the Spectrum [1/sqrt(Hz)]."
    )
    start_time: str = Field(
        description="The ISO UTC start time the spectrum was taken."
    )
    end_time: str = Field(description="The ISO UTC end time the spectrum was taken.")
    detector_id: int = Field(
        description="ID of the MMADetector that acquired the Spectrum."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description='IDs of the Groups to share this spectrum with. Set to "all" '
        "to make this spectrum visible to all users.",
    )


class MMADetectorSpectrumPatchBody(BaseModel):
    """Request body for updating an MMADetector spectrum."""

    model_config = ConfigDict(extra="forbid")

    frequencies: list[float] | None = Field(
        default=None, description="Frequencies of the spectrum [Hz]."
    )
    amplitudes: list[float] | None = Field(
        default=None, description="Amplitude of the Spectrum [1/sqrt(Hz)]."
    )
    start_time: str | None = Field(
        default=None, description="The ISO UTC start time the spectrum was taken."
    )
    end_time: str | None = Field(
        default=None, description="The ISO UTC end time the spectrum was taken."
    )
    detector_id: int | None = Field(
        default=None, description="ID of the MMADetector that acquired the Spectrum."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description='IDs of the Groups to share this spectrum with. Set to "all" '
        "to make this spectrum visible to all users.",
    )


class MMADetectorSpectrumPostResponse(BaseModel):
    """Data payload returned when uploading an MMADetector spectrum."""

    id: int = Field(description="New mmadetector spectrum ID")


class MMADetectorTimeIntervalPostBody(BaseModel):
    """Request body for uploading MMADetector time interval(s)."""

    model_config = ConfigDict(extra="forbid")

    detector_id: int | None = Field(
        default=None, description="ID of the MMADetector for the time interval(s)."
    )
    time_interval: list | None = Field(
        default=None, description="A single time interval [start, end]."
    )
    time_intervals: list | None = Field(
        default=None, description="List of time intervals, each [start, end]."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description="IDs of the Groups to share these time intervals with. Set to "
        '"all" to make them visible to all users.',
    )


class MMADetectorTimeIntervalPatchBody(BaseModel):
    """Request body for updating an MMADetector time interval."""

    model_config = ConfigDict(extra="forbid")

    detector_id: int | None = Field(
        default=None, description="ID of the MMADetector for the time interval."
    )
    time_interval: list | None = Field(
        default=None, description="A time interval [start, end]."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description="IDs of the Groups to share this time interval with. Set to "
        '"all" to make it visible to all users.',
    )


class MMADetectorTimeIntervalPostResponse(BaseModel):
    """Data payload returned when uploading MMADetector time interval(s)."""

    ids: list[int] = Field(description="New mmadetector time interval IDs")


class MMADetectorSpectrumGetQuery(BaseModel):
    """Query parameters for listing MMA Detector spectra."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    observedBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only spectra observed before this time."
        ),
    )
    observedAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only spectra observed after this time."
        ),
    )
    detectorIDs: list[int] | None = Field(
        default=None,
        description="If provided, filter only spectra observed with one of these mmadetector IDs.",
    )
    groupIDs: list[int] | None = Field(
        default=None,
        description="If provided, filter only spectra saved to one of these group IDs.",
    )


class MMADetectorTimeIntervalGetQuery(BaseModel):
    """Query parameters for listing MMA Detector time intervals."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    observedBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only time intervals observed before this time."
        ),
    )
    observedAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only time intervals observed after this time."
        ),
    )
    detectorIDs: list[int] | None = Field(
        default=None,
        description=(
            "If provided, filter only time intervals observed with one of these "
            "mmadetector IDs."
        ),
    )
    groupIDs: list[int] | None = Field(
        default=None,
        description="If provided, filter only time intervals saved to one of these group IDs.",
    )
