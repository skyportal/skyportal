"""Response models for spectra."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.annotations import AnnotationDetailResponse
from skyportal_py_models.comments import CommentDetailResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.instruments import InstrumentResponse
from skyportal_py_models.users import UserResponse


class _SpectrumBaseResponse(BaseModel):
    """A spectrum of a source."""

    # ``instrument_name``, ``telescope_id``, ``telescope_name``, ``comments``,
    # ``annotations`` and the ``external_*`` names are injected by the handlers
    # rather than being columns, and the ``external_*`` keys are only present
    # when the spectrum records an external PI/reducer/observer.
    # ``original_file_string`` is deferred and only returned when explicitly
    # requested.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    # typed as dict to avoid an import cycle with sources
    obj: dict[str, Any] | None = None
    observed_at: datetime | None = None
    wavelengths: list[float] = Field(default_factory=list)
    fluxes: list[float] = Field(default_factory=list)
    errors: list[float] | None = None
    units: str | None = None
    origin: str | None = None
    type: str | None = None
    label: str | None = None
    instrument_id: int | None = None
    instrument: InstrumentResponse | None = None
    instrument_name: str | None = None
    telescope_id: int | None = None
    telescope_name: str | None = None
    followup_request_id: int | None = None
    assignment_id: int | None = None
    altdata: dict[str, Any] | None = None
    original_file_string: str | None = None
    original_file_filename: str | None = None
    owner_id: int | None = None
    owner: UserResponse | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    pis: list[UserResponse] = Field(default_factory=list)
    reducers: list[UserResponse] = Field(default_factory=list)
    observers: list[UserResponse] = Field(default_factory=list)
    external_pi: str | None = None
    external_reducer: str | None = None
    external_observer: str | None = None
    comments: list[CommentDetailResponse] = Field(default_factory=list)
    annotations: list[AnnotationDetailResponse] = Field(default_factory=list)


class SpectrumResponse(_SpectrumBaseResponse):
    """A spectrum, as returned by the single-spectrum and per-object routes."""

    # ``GET /api/sources/{obj_id}/spectra`` additionally injects
    # ``observed_at_mjd``, adds a ``gravatar_url`` to each comment's author,
    # and adds a constant ``type`` key to each annotation.

    observed_at_mjd: float | None = None


class SpectrumDetailResponse(_SpectrumBaseResponse):
    """A spectrum with the full payload the server can attach to it."""


class ParsedSpectrumResponse(BaseModel):
    """A spectrum parsed from ASCII but not saved to the database."""

    # The parse endpoint returns an unsaved ``Spectrum``, so only the
    # attributes the parser set are present: no ``id``, ``created_at`` or
    # ``modified``, and no ``units``/``origin``/``followup_request_id``/
    # ``assignment_id``, which are only set when a spectrum is saved.

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    observed_at: datetime | None = None
    wavelengths: list[float] = Field(default_factory=list)
    fluxes: list[float] = Field(default_factory=list)
    errors: list[float] | None = None
    units: str | None = None
    origin: str | None = None
    type: str | None = None
    label: str | None = None
    instrument_id: int | None = None
    followup_request_id: int | None = None
    assignment_id: int | None = None
    altdata: dict[str, Any] | None = None
    original_file_string: str | None = None
    original_file_filename: str | None = None
    owner_id: int | None = None


class SourceSpectraResponse(BaseModel):
    """Envelope of a source's spectra response."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = None
    spectra: list[SpectrumResponse] = Field(default_factory=list)


class BulkSpectraSourceResponse(BaseModel):
    """Phase anchors for one source in a bulk spectra response."""

    model_config = ConfigDict(extra="forbid")

    id: str
    redshift: float | None = None
    first_detected_mjd: float | None = None
    peak_mjd: float | None = None
    tns_discovery_date: str | None = None


class BulkSpectrumResponse(BaseModel):
    """A slim spectrum returned by the bulk spectra endpoint."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = None
    observed_at: str | None = None
    wavelengths: list[float] = Field(default_factory=list)
    fluxes: list[float] = Field(default_factory=list)


class BulkSpectraResponse(BaseModel):
    """Result of a bulk spectra query."""

    model_config = ConfigDict(extra="forbid")

    sources: list[BulkSpectraSourceResponse] = Field(default_factory=list)
    spectra: list[BulkSpectrumResponse] = Field(default_factory=list)
    truncated: bool = False


class SpectrumPost(BaseModel):
    """Payload for posting a spectrum."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    instrument_id: int
    observed_at: str
    wavelengths: list[float]
    fluxes: list[float]
    errors: list[float] | None = None
    units: str | None = None
    origin: str | None = None
    type: str | None = None
    label: str | None = None
    altdata: dict[str, Any] | None = None
    followup_request_id: int | None = None
    assignment_id: int | None = None
    group_ids: list[int] | str | None = None
    pi: list[int] | None = None
    external_pi: str | None = None
    reduced_by: list[int] | None = None
    external_reducer: str | None = None
    observed_by: list[int] | None = None
    external_observer: str | None = None


class SpectrumUpdate(BaseModel):
    """Payload for updating a spectrum; every field is optional."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = None
    instrument_id: int | None = None
    observed_at: str | None = None
    wavelengths: list[float] | None = None
    fluxes: list[float] | None = None
    errors: list[float] | None = None
    units: str | None = None
    origin: str | None = None
    type: str | None = None
    label: str | None = None
    altdata: dict[str, Any] | None = None
    followup_request_id: int | None = None
    assignment_id: int | None = None
    group_ids: list[int] | str | None = None
    pi: list[int] | None = None
    external_pi: str | None = None
    reduced_by: list[int] | None = None
    external_reducer: str | None = None
    observed_by: list[int] | None = None
    external_observer: str | None = None


class SpectrumAsciiParse(BaseModel):
    """Payload for parsing an ASCII spectrum without saving it."""

    model_config = ConfigDict(extra="forbid")

    ascii: str
    wave_column: int | None = None
    flux_column: int | None = None
    fluxerr_column: int | None = None


class SpectrumAsciiPost(BaseModel):
    """Payload for uploading a spectrum from an ASCII file."""

    model_config = ConfigDict(extra="forbid")

    ascii: str
    obj_id: str
    instrument_id: int
    observed_at: str
    filename: str
    wave_column: int | None = None
    flux_column: int | None = None
    fluxerr_column: int | None = None
    type: str | None = None
    label: str | None = None
    group_ids: list[int] | str | None = None
    pi: list[int] | None = None
    external_pi: str | None = None
    reduced_by: list[int] | None = None
    external_reducer: str | None = None
    observed_by: list[int] | None = None
    external_observer: str | None = None
    followup_request_id: int | None = None
    assignment_id: int | None = None
