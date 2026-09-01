"""Response models for ``/api/observation``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

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


class ObservationPost(BaseModel):
    """Payload for ingesting a set of executed observations."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    telescope_name: str = Field(alias="telescopeName")
    instrument_name: str = Field(alias="instrumentName")
    observation_data: dict[str, list[Any]] = Field(alias="observationData")


MAX_OBSERVATIONS = 10000


class ObservationGetQuery(BaseModel):
    """Query parameters for retrieving observations."""

    model_config = ConfigDict(extra="forbid")

    telescopeName: str | None = Field(
        default=None, description="Filter by telescope name"
    )
    instrumentName: str | None = Field(
        default=None, description="Filter by instrument name"
    )
    startDate: str | None = Field(default=None, description="Filter by start date")
    endDate: str | None = Field(default=None, description="Filter by end date")
    localizationDateobs: str | None = Field(
        default=None,
        description=(
            "Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). Each "
            "localization is associated with a specific GCNEvent by the date the "
            "event happened, and this date is used as a unique identifier. It can "
            "be therefore found as Localization.dateobs, queried from the "
            "/api/localization endpoint or dateobs in the GcnEvent page table."
        ),
    )
    localizationName: str | None = Field(
        default=None,
        description=(
            "Name of localization / skymap to use. Can be found in "
            "Localization.localization_name queried from /api/localization "
            "endpoint or skymap name in GcnEvent page table."
        ),
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include fields. Defaults to 0.95.",
    )
    numberObservations: int = Field(
        default=1,
        description=(
            "Minimum number of observations of a field required to include. Defaults to 1."
        ),
    )
    returnStatistics: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include integrated probability and area. "
            "Defaults to false."
        ),
    )
    statsMethod: Literal["python", "db"] = Field(
        default="python",
        description=(
            "Method to use for computing integrated probability and area. Defaults "
            "to 'python'. To use the database/postgres based method, use 'db'."
        ),
    )
    statsLogging: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to log the stats computation time. Defaults to false."
        ),
    )
    includeGeoJSON: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated GeoJSON. Defaults to false."
        ),
    )
    observationStatus: Literal["executed", "queued"] = Field(
        default="executed",
        description="Whether to include queued or executed observations. Defaults to executed.",
    )
    pageNumber: int = Field(
        default=1, description="Page number for paginated query results. Defaults to 1."
    )
    numPerPage: int = Field(
        default=100,
        description=(
            f"Number of observations to return per paginated request. Defaults to "
            f"100. Can be no larger than {MAX_OBSERVATIONS}."
        ),
    )
    sortBy: str | None = Field(default=None, description="The field to sort by.")
    sortOrder: str = Field(
        default="asc",
        description="The sort order - either 'asc' or 'desc'. Defaults to 'asc'.",
    )


class ObservationPostBody(BaseModel):
    """Request body for ingesting a set of ExecutedObservations."""

    model_config = ConfigDict(extra="forbid")

    telescopeName: str | None = Field(
        None, description="The telescope name associated with the fields"
    )
    instrumentName: str | None = Field(
        None, description="The instrument name associated with the fields"
    )
    observationData: dict | None = Field(
        default_factory=dict, description="Observation data dictionary list"
    )


class ObservationASCIIFilePostBody(BaseModel):
    """Request body for uploading observations from an ASCII file."""

    model_config = ConfigDict(extra="forbid")

    instrumentID: int | str | None = Field(
        None, description="The instrument ID associated with the fields"
    )
    observationData: str | None = Field(
        None, description="Observation data Ascii string"
    )


class ObservationExternalAPIGetQuery(BaseModel):
    """Query parameters for retrieving queued observations from an external API."""

    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(
        default=None,
        description="Filter by start date",
    )
    endDate: str | None = Field(
        default=None,
        description="Filter by end date",
    )
    queuesOnly: bool = Field(
        default=False,
        description="Return queue only (do not commit observations)",
    )


class ObservationExternalAPIPostBody(BaseModel):
    """Request body for retrieving observations from an external API."""

    model_config = ConfigDict(extra="forbid")

    start_date: str | None = Field(None, description="start date of the request.")
    end_date: str | None = Field(None, description="end date of the request.")
    allocation_id: int | None = Field(
        None, description="Followup request allocation ID."
    )


class ObservationExternalAPIDeleteBody(BaseModel):
    """Request body for deleting queued observations from an external API."""

    model_config = ConfigDict(extra="forbid")

    queueName: str | None = Field(None, description="Queue name to remove")


class ObservationTreasureMapPostQuery(BaseModel):
    """Query parameters for submitting observations to TreasureMap.

    Everything else this endpoint reads comes from the JSON body.
    """

    model_config = ConfigDict(extra="forbid")

    numberObservations: int = Field(
        default=1,
        description=(
            "Minimum number of observations of a field required to include. Defaults to 1."
        ),
    )


class ObservationTreasureMapPostBody(BaseModel):
    """Request body for submitting executed observations to TreasureMap."""

    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(None, description="Filter by start date")
    endDate: str | None = Field(None, description="Filter by end date")
    localizationDateobs: str | None = Field(
        None,
        description=(
            "Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). "
            "Each localization is associated with a specific GCNEvent by "
            "the date the event happened, and this date is used as a unique "
            "identifier. It can be therefore found as Localization.dateobs, "
            "queried from the /api/localization endpoint or dateobs in the "
            "GcnEvent page table."
        ),
    )
    localizationName: str | None = Field(
        None,
        description=(
            "Name of localization / skymap to use. "
            "Can be found in Localization.localization_name queried from "
            "/api/localization endpoint or skymap name in GcnEvent page table."
        ),
    )
    localizationCumprob: float = Field(
        0.95,
        description=(
            "Cumulative probability up to which to include fields. Defaults to 0.95."
        ),
    )


class ObservationTreasureMapDeleteBody(BaseModel):
    """Request body for removing executed observations from TreasureMap."""

    model_config = ConfigDict(extra="forbid")

    localizationDateobs: str | None = Field(
        None,
        description=(
            "Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). "
            "Each localization is associated with a specific GCNEvent by "
            "the date the event happened, and this date is used as a unique "
            "identifier. It can be therefore found as Localization.dateobs, "
            "queried from the /api/localization endpoint or dateobs in the "
            "GcnEvent page table."
        ),
    )


class ObservationSimSurveyGetQuery(BaseModel):
    """Query parameters for performing a simsurvey efficiency calculation."""

    model_config = ConfigDict(extra="forbid")

    startDate: str = Field(description="Filter by start date")
    endDate: str = Field(description="Filter by end date")
    localizationDateobs: str = Field(
        description=(
            "Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). "
            "Each localization is associated with a specific GCNEvent by "
            "the date the event happened, and this date is used as a unique "
            "identifier. It can be therefore found as Localization.dateobs, "
            "queried from the /api/localization endpoint or dateobs in the "
            "GcnEvent page table."
        ),
    )
    localizationName: str | None = Field(
        default=None,
        description=(
            "Name of localization / skymap to use. "
            "Can be found in Localization.localization_name queried from "
            "/api/localization endpoint or skymap name in GcnEvent page table."
        ),
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include fields. Defaults to 0.95.",
    )
    numberInjections: int = Field(
        default=1000,
        description="Number of simulations to evaluate efficiency with. Defaults to 1000.",
    )
    numberDetections: int = Field(
        default=1,
        description="Number of detections required for detection. Defaults to 1.",
    )
    detectionThreshold: float = Field(
        default=5,
        description="Threshold (in sigmas) required for detection. Defaults to 5.",
    )
    minimumPhase: float = Field(
        default=0,
        description="Minimum phase (in days) post event time to consider detections. Defaults to 0.",
    )
    maximumPhase: float = Field(
        default=3,
        description="Maximum phase (in days) post event time to consider detections. Defaults to 3.",
    )
    modelName: str = Field(
        default="kilonova",
        description=(
            "Model to simulate efficiency for. Must be one of kilonova, "
            "afterglow, or linear. Defaults to kilonova."
        ),
    )
    optionalInjectionParameters: str = Field(
        default="{}",
        description=(
            "JSON-encoded object of optional parameters to specify the "
            "injection type, along with a list of possible values (to be "
            "used in a dropdown UI)"
        ),
    )
    group_ids: list[int] | None = Field(
        default=None,
        description=(
            "List of group IDs corresponding to which groups should be "
            "able to view the analyses. Defaults to all of requesting user's "
            "groups."
        ),
    )
