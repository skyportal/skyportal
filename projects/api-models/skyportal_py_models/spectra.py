"""Response models for spectra."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

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


# The pydantic request models below gate the top-level body shape (allowed keys +
# extra="forbid"); the existing marshmallow schemas (SpectrumPost, the ASCII
# JSON schemas) keep doing the deep per-field validation on model_dump().
class SpectrumPostBody(BaseModel):
    """Request body for uploading/updating a spectrum (see SpectrumPost)."""

    model_config = ConfigDict(extra="forbid")

    # Array elements may be null; the downstream marshmallow schema enforces the
    # real per-element rules (see the photometry migration null-element bug).
    wavelengths: list[float | None] | None = Field(
        default=None, description="Wavelengths of the spectrum [Angstrom]."
    )
    fluxes: list[float | None] | None = Field(
        default=None,
        description="Flux of the Spectrum [F_lambda, arbitrary units].",
    )
    errors: list[float | None] | None = Field(
        default=None,
        description="Errors on the fluxes of the spectrum [F_lambda, same units as "
        "`fluxes`.]",
    )
    units: str | None = Field(
        default=None,
        description="Units of the fluxes/errors. Options are Jy, AB, or "
        "erg/s/cm/cm/AA).",
    )
    obj_id: str | None = Field(default=None, description="ID of this Spectrum's Obj.")
    observed_at: str | None = Field(
        default=None, description="The ISO UTC time the spectrum was taken."
    )
    pi: list[int] | None = Field(
        default=None,
        description="IDs of the Users who are PI of this Spectrum, or to use as "
        "points of contact given an external PI.",
    )
    external_pi: str | None = Field(
        default=None, description="Free text provided as an external PI"
    )
    reduced_by: list[int] | None = Field(
        default=None,
        description="IDs of the Users who reduced this Spectrum, or to use as points "
        "of contact given an external reducer.",
    )
    external_reducer: str | None = Field(
        default=None, description="Free text provided as an external reducer"
    )
    observed_by: list[int] | None = Field(
        default=None,
        description="IDs of the Users who observed this Spectrum, or to use as points "
        "of contact given an external observer.",
    )
    external_observer: str | None = Field(
        default=None, description="Free text provided as an external observer"
    )
    origin: str | None = Field(default=None, description="Origin of the spectrum.")
    type: str | None = Field(
        default=None,
        description="Type of spectrum. One of the configured allowed spectrum types.",
    )
    label: str | None = Field(
        default=None,
        description="User defined label (can be used to replace default "
        "instrument/date labeling on plot legends).",
    )
    instrument_id: int | None = Field(
        default=None,
        description="ID of the Instrument that acquired the Spectrum.",
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description='IDs of the Groups to share this spectrum with. Set to "all" to '
        "make this spectrum visible to all users.",
    )
    followup_request_id: int | None = Field(
        default=None,
        description="ID of the Followup request that generated this spectrum, if any.",
    )
    assignment_id: int | None = Field(
        default=None,
        description="ID of the classical assignment that generated this spectrum, "
        "if any.",
    )
    altdata: dict[str, Any] | None = Field(
        default=None, description="Miscellaneous alternative metadata."
    )


class SpectrumPostResponse(BaseModel):
    """Data payload returned when uploading a spectrum."""

    id: int = Field(description="New spectrum ID")


class SpectrumASCIIParseBody(BaseModel):
    """Request body for parsing a spectrum from an ASCII file (see
    SpectrumAsciiFileParseJSON)."""

    model_config = ConfigDict(extra="forbid")

    wave_column: int | None = Field(
        default=None,
        description="The 0-based index of the ASCII column corresponding to the "
        "wavelength values of the spectrum (default 0).",
    )
    flux_column: int | None = Field(
        default=None,
        description="The 0-based index of the ASCII column corresponding to the flux "
        "values of the spectrum (default 1).",
    )
    fluxerr_column: int | None = Field(
        default=None,
        description="The 0-based index of the ASCII column corresponding to the flux "
        "error values of the spectrum (default None). If a column for errors is "
        "provided, set to the corresponding 0-based column number, otherwise, it "
        "will be ignored.",
    )
    ascii: str | None = Field(
        default=None, description="The content of the ASCII file to be parsed."
    )


class SpectrumASCIIPostBody(SpectrumASCIIParseBody):
    """Request body for uploading a spectrum from an ASCII file (see
    SpectrumAsciiFilePostJSON)."""

    obj_id: str | None = Field(
        default=None, description="The ID of the object that the spectrum is of."
    )
    instrument_id: int | None = Field(
        default=None, description="The ID of the instrument that took the spectrum."
    )
    type: str | None = Field(
        default=None,
        description="Type of spectrum. One of the configured allowed spectrum types.",
    )
    label: str | None = Field(
        default=None,
        description="User defined label to be placed in plot legends, instead of the "
        "default <instrument>-<date taken>.",
    )
    observed_at: str | None = Field(
        default=None, description="The ISO UTC time the spectrum was taken."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description="The IDs of the groups to share this spectrum with.",
    )
    filename: str | None = Field(
        default=None,
        description="The original filename (for bookkeeping purposes).",
    )
    pi: list[int] | None = Field(
        default=None,
        description="IDs of the Users who are PI of this Spectrum, or to use as "
        "points of contact given an external PI.",
    )
    external_pi: str | None = Field(
        default=None, description="Free text provided as an external PI"
    )
    reduced_by: list[int] | None = Field(
        default=None,
        description="IDs of the Users who reduced this Spectrum, or to use as points "
        "of contact given an external reducer.",
    )
    external_reducer: str | None = Field(
        default=None, description="Free text provided as an external reducer"
    )
    observed_by: list[int] | None = Field(
        default=None,
        description="IDs of the Users who observed this Spectrum, or to use as points "
        "of contact given an external observer.",
    )
    external_observer: str | None = Field(
        default=None, description="Free text provided as an external observer"
    )
    followup_request_id: int | None = Field(
        default=None,
        description="ID of the Followup request that generated this spectrum, if any.",
    )
    assignment_id: int | None = Field(
        default=None,
        description="ID of the classical assignment that generated this spectrum, "
        "if any.",
    )


class SpectrumASCIIPostResponse(BaseModel):
    """Data payload returned when uploading a spectrum from an ASCII file."""

    id: int = Field(description="New spectrum ID")


class BulkSpectraPostBody(BaseModel):
    """Request body for the bulk spectra endpoint."""

    model_config = ConfigDict(extra="forbid")

    group_id: int | None = Field(
        default=None, description="Restrict to sources saved to this group."
    )
    obj_ids: list[str] | str | None = Field(
        default=None,
        description="Restrict to these object IDs (also accepts a comma-separated "
        "string).",
    )
    classifications: list[str] | str | None = Field(
        default=None,
        description="Restrict to sources with any of these (non-ML) classifications.",
    )
    classificationProbThreshold: float | None = Field(
        default=None,
        description="Only count classifications at or above this probability.",
    )
    maxSources: int | None = Field(
        default=None,
        description="Max sources to fetch spectra for (default 200, capped at 1000).",
    )


class SyntheticPhotometryPostBody(BaseModel):
    """Request body for creating synthetic photometry from a spectrum."""

    model_config = ConfigDict(extra="forbid")

    filters: list[str] | None = Field(default=None, description="List of filters")


class SpectrumGetQuery(BaseModel):
    """Query parameters for retrieving a single spectrum or multiple spectra."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"includeOriginalFile"})

    includeOriginalFile: bool = Field(
        default=False,
        description=(
            "If true, include the raw uploaded spectrum file "
            "(original_file_string) in each spectrum. Defaults to false; "
            "when omitted, that field is neither loaded nor returned. "
            "Ignored when minimalPayload is true (which never includes it)."
        ),
    )
    minimalPayload: bool = Field(
        default=False,
        description=(
            "If true, return only the minimal metadata "
            "about each spectrum, instead of returning "
            "the potentially large payload that includes "
            "wavelength/flux and also comments and annotations. "
            "The metadata that is always included is: "
            "id, obj_id, owner_id, origin, type, label, "
            "observed_at, created_at, modified, "
            "instrument_id, instrument_name, original_file_name, "
            "followup_request_id, assignment_id, and altdata."
        ),
    )
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
    modifiedBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only spectra modified before this time."
        ),
    )
    modifiedAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only spectra modified after this time."
        ),
    )
    objID: str | None = Field(
        default=None,
        description=(
            "Return any spectra on an object with ID that has a (partial) match "
            'to this argument (i.e., the given argument is "in" the object\'s ID).'
        ),
    )
    instrumentIDs: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of integer instrument IDs. If provided, "
            "filter only spectra observed with one of these instrument IDs."
        ),
    )
    groupIDs: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of integer group IDs. If provided, filter "
            "only spectra saved to one of these group IDs."
        ),
    )
    followupRequestIDs: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of integer followup request IDs. If "
            "provided, filter only spectra associate with these followup "
            "request IDs."
        ),
    )
    assignmentIDs: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of integer assignment IDs. If provided, "
            "filter only spectra associate with these assignment request IDs."
        ),
    )
    origin: str | None = Field(
        default=None,
        description=(
            "Return any spectra that have an origin with a (partial) match "
            "to any of the values in this comma separated list."
        ),
    )
    label: str | None = Field(
        default=None,
        description=(
            "Return any spectra that have a label with a (partial) match "
            "to any of the values in this comma separated list."
        ),
    )
    type: str | None = Field(
        default=None,
        description=(
            "Return spectra of the given type or types "
            "(match multiple values using a comma separated list). "
            "Types of spectra are defined in the config, "
            "e.g., source, host or host_center."
        ),
    )
    commentsFilter: str | None = Field(
        default=None,
        description=(
            "Comma-separated string of comment text to filter for spectra matching."
        ),
    )
    commentsFilterAuthor: str | None = Field(
        default=None,
        description=(
            "Comma separated string of authors. "
            "Only comments from these authors are used "
            "when filtering with the commentsFilter."
        ),
    )
    commentsFilterBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "only return sources that have comments before this time."
        ),
    )
    commentsFilterAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "only return sources that have comments after this time."
        ),
    )


class ObjSpectraGetQuery(BaseModel):
    """Query parameters for retrieving all spectra associated with an Object."""

    model_config = ConfigDict(extra="forbid")

    normalization: Literal["median"] | None = Field(
        default=None,
        description=(
            'what normalization is needed for the spectra (e.g., "median"). '
            "If omitted, returns the original spectrum. "
            "Options for normalization are: "
            "median: normalize the flux to have median==1"
        ),
    )
    sortBy: Literal["observed_at", "created_at"] = Field(
        default="observed_at",
        description=(
            "The column to order the spectra by. Defaults to observed_at. "
            "Options are: observed_at, created_at"
        ),
    )
    sortOrder: Literal["asc", "desc"] = Field(
        default="asc",
        description=(
            "The order to sort the spectra by. Defaults to asc. Options are: asc, desc"
        ),
    )
    includeOriginalFile: bool = Field(
        default=False,
        description=(
            "If true, include the raw uploaded spectrum file "
            "(original_file_string) in each spectrum. Defaults to false; "
            "when omitted, that field is neither loaded nor returned."
        ),
    )


class SpectrumRangeGetQuery(BaseModel):
    """Query parameters for retrieving spectra within a date range."""

    model_config = ConfigDict(extra="forbid")

    instrument_ids: list[int] = Field(
        default_factory=list,
        description=(
            "Instrument id numbers of spectrum. If None, retrieve for all instruments."
        ),
    )
    min_date: str | None = Field(
        default=None,
        description=(
            "Minimum UTC date of range in ISOT format. If None, open ended range."
        ),
    )
    max_date: str | None = Field(
        default=None,
        description=(
            "Maximum UTC date of range in ISOT format. If None, open ended range."
        ),
    )
