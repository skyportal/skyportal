"""Response models for ``/api/candidates``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.annotations import AnnotationResponse
from skyportal_py_models.classifications import ClassificationResponse
from skyportal_py_models.comments import CommentResponse
from skyportal_py_models.galaxies import GalaxyResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.objs import ObjBody
from skyportal_py_models.tags import ObjTagResponse
from skyportal_py_models.thumbnails import ThumbnailResponse


class CandidatePassingAlertResponse(BaseModel):
    """One alert that made an object pass a filter (a ``Candidate`` row)."""

    model_config = ConfigDict(extra="forbid")

    filter_id: int | None = None
    passing_alert_id: int | None = None
    passed_at: datetime | None = None


class CandidateAssociatedObjResponse(BaseModel):
    """Another object linked to a candidate through a ``SuperObj``."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = None
    ra: float | None = None
    dec: float | None = None
    separation: float | None = None
    super_obj_id: int | None = None
    super_obj_name: str | None = None


class CandidateResponse(BaseModel):
    """An object that passed a filter: the serialized ``Obj`` columns plus
    the scanning extras the candidate endpoints graft onto them."""

    # The ``photometry``, ``spectra`` and ``followup_requests`` payloads keep
    # their eager-loaded relationships inline and stay ``dict``.

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime | None = None
    modified: datetime | None = None
    ra: float | None = None
    dec: float | None = None
    ra_dis: float | None = None
    dec_dis: float | None = None
    ra_err: float | None = None
    dec_err: float | None = None
    offset: float | None = None
    t0: float | None = None
    redshift: float | None = None
    redshift_error: float | None = None
    redshift_origin: str | None = None
    redshift_history: list[dict[str, Any]] | None = None
    host_id: int | None = None
    summary: str | None = None
    summary_history: list[dict[str, Any]] | None = None
    altdata: dict[str, Any] | None = None
    dist_nearest_source: float | None = None
    mag_nearest_source: float | None = None
    e_mag_nearest_source: float | None = None
    transient: bool | None = None
    varstar: bool | None = None
    is_roid: bool | None = None
    mpc_name: str | None = None
    tns_name: str | None = None
    tns_info: dict[str, Any] | None = None
    score: float | None = None
    origin: str | None = None
    alias: list[str] | None = None
    healpix: int | None = None
    detect_photometry_count: int | None = None
    internal_key: str | None = None

    # Relationships the handlers eager-load.
    thumbnails: list[ThumbnailResponse] | None = None
    photstats: list[dict[str, Any]] | None = None
    host: GalaxyResponse | None = None

    # Keys the handlers inject.
    is_source: bool | int | None = None
    saved_groups: list[GroupResponse] | None = None
    classifications: list[ClassificationResponse] | None = None
    passing_group_ids: list[int] | None = None
    filter_ids: list[int] | None = None
    passing_alerts: list[CandidatePassingAlertResponse] | None = None
    tags: list[ObjTagResponse] | None = None
    annotations: list[AnnotationResponse] | None = None
    comments: list[CommentResponse] | None = None
    photometry: list[dict[str, Any]] | None = None
    spectra: list[dict[str, Any]] | None = None
    followup_requests: list[dict[str, Any]] | None = None
    associated_objs: list[CandidateAssociatedObjResponse] | None = None
    last_detected_at: datetime | None = None
    gal_lon: float | None = None
    gal_lat: float | None = None
    luminosity_distance: float | None = None
    dm: float | None = None
    angular_diameter_distance: float | None = None


class CandidatesPageResponse(BaseModel):
    """One page of results from a candidates query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    # The name-only autocomplete form returns bare {"candidates": [...]}
    # with no pagination keys, so totalMatches cannot be required.
    candidates: list[CandidateResponse]
    total_matches: int | None = Field(alias="totalMatches", default=None)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=25)
    query_id: str | None = Field(alias="queryID", default=None)


class CandidatePostResponse(BaseModel):
    """Result of posting a new candidate."""

    model_config = ConfigDict(extra="forbid")

    ids: list[int] = Field(default_factory=list)


class BulkCandidateDeleteResponse(BaseModel):
    """Result of a bulk deletion of old, unsaved candidate objects."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    deleted: int
    remaining: int
    dry_run: bool = Field(alias="dryRun")


class CandidateRecordResponse(BaseModel):
    """One row of the ``candidates`` table (a ``Candidate``)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    filter_id: int | None = None
    passed_at: datetime | None = None
    passing_alert_id: int | None = None
    uploader_id: int | None = None


class CandidateFilterPageResponse(BaseModel):
    """One page of raw candidate rows from ``/api/candidates_filter``."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    # totalMatches is only computed on page 1.
    candidates: list[CandidateRecordResponse] = Field(default_factory=list)
    total_matches: int | None = Field(alias="totalMatches", default=None)


class ScanReportResponse(BaseModel):
    """A candidate scanning report (a ``ScanReport``)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    author_id: int | None = None
    # The handler substitutes the author's username for the relationship.
    author: str | None = None
    options: dict[str, Any] | None = None
    groups: list[GroupResponse] | None = None


class ScanReportsPageResponse(BaseModel):
    """One page of candidate scanning reports."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    reports: list[ScanReportResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches")
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=10)


class ScanReportItemResponse(BaseModel):
    """One saved candidate listed in a scanning report."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    scan_report_id: int | None = None
    data: dict[str, Any] | None = None


class CandidatePost(BaseModel):
    """Payload for posting a new candidate.

    Beyond the candidate's own fields, the server loads the body with the
    ``Obj`` schema, so any ``Obj`` column may be set when the object does
    not exist yet (and is updated in place when it does).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    ra: float
    dec: float
    filter_ids: list[int]
    passed_at: str
    passing_alert_id: int | None = None
    ra_dis: float | None = None
    dec_dis: float | None = None
    ra_err: float | None = None
    dec_err: float | None = None
    offset: float | None = None
    t0: float | None = None
    redshift: float | None = None
    redshift_error: float | None = None
    redshift_origin: str | None = None
    host_id: int | None = None
    summary: str | None = None
    altdata: dict[str, Any] | None = None
    dist_nearest_source: float | None = None
    mag_nearest_source: float | None = None
    e_mag_nearest_source: float | None = None
    transient: bool | None = None
    varstar: bool | None = None
    is_roid: bool | None = None
    mpc_name: str | None = None
    tns_name: str | None = None
    tns_info: dict[str, Any] | None = None
    score: float | None = None
    origin: str | None = None
    alias: list[str] | None = None
    detect_photometry_count: int | None = None


class ScanReportPassedFiltersRange(BaseModel):
    """Time range over which candidates must have passed a filter."""

    model_config = ConfigDict(extra="forbid")

    start_date: str
    end_date: str


class ScanReportSavedCandidatesRange(BaseModel):
    """Time range over which candidates must have been saved as sources."""

    model_config = ConfigDict(extra="forbid")

    start_saved_date: str
    end_saved_date: str


class ScanReportPost(BaseModel):
    """Payload for generating a candidate scanning report."""

    model_config = ConfigDict(extra="forbid")

    group_ids: list[int]
    passed_filters_range: ScanReportPassedFiltersRange | None = None
    saved_candidates_range: ScanReportSavedCandidatesRange | None = None
    passed_filters_window_hours: float | None = None
    saved_candidates_window_hours: float | None = None
    gcn_event_dateobs: str | None = None


SAVED_STATUSES = (
    "all",
    "savedToAllSelected",
    "savedToAnySelected",
    "savedToAnyAccessible",
    "notSavedToAnyAccessible",
    "notSavedToAnySelected",
    "notSavedToAllSelected",
)


class CandidateGetQuery(BaseModel):
    """Query parameters for retrieving a single candidate or querying candidates."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"includeAlerts"})

    numPerPage: int = Field(
        default=25,
        description=(
            "Number of candidates to return per paginated request. Defaults to 25. "
            "Capped at 500."
        ),
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1",
    )
    autosave: bool = Field(
        default=False,
        description="Automatically save candidates passing query.",
    )
    autosaveGroupIds: list[int] | None = Field(
        default=None,
        description="Group ID(s) to save candidates to.",
    )
    savedStatus: Literal[*SAVED_STATUSES] = Field(
        default="all",
        description=(
            "String indicating the saved status to filter candidate results for. "
            "Must be one of the enumerated values."
        ),
    )
    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "Candidate.passed_at >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "Candidate.passed_at <= endDate"
        ),
    )
    groupIDs: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of group IDs (e.g. "1,2"). Defaults to all of '
            "user's groups if filterIDs is not provided."
        ),
    )
    filterIDs: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of filter IDs (e.g. "1,2"). Defaults to all of '
            "user's groups' filters if groupIDs is not provided."
        ),
    )
    sortByAnnotationOrigin: str | None = Field(
        default=None,
        description="The origin of the Annotation to sort by",
    )
    sortByAnnotationKey: str | None = Field(
        default=None,
        description="The key of the Annotation data value to sort by",
    )
    sortByAnnotationOrder: str | None = Field(
        default=None,
        description=(
            'The sort order for annotations - either "asc" or "desc". '
            'Defaults to "asc".'
        ),
    )
    annotationFilterList: str | None = Field(
        default=None,
        description=(
            "Comma-separated string of JSON objects representing annotation filters. "
            "Filter objects are expected to have keys { origin, key, value } for "
            "non-numeric value types, or { origin, key, min, max } for numeric values."
        ),
    )
    includePhotometry: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated photometry. "
            "Defaults to false."
        ),
    )
    includeSpectra: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated spectra. "
            "Defaults to false."
        ),
    )
    includeComments: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated comments. "
            "Defaults to false."
        ),
    )
    includeFollowupRequests: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated follow-up requests. "
            "Defaults to false."
        ),
    )
    includeAssociatedObjs: bool = Field(
        default=True,
        description=(
            "Boolean indicating whether to include associated objects (objects "
            "grouped under the same super-object). Defaults to true."
        ),
    )
    includeAlerts: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated alerts. "
            "Defaults to false."
        ),
    )
    classifications: list[str] | None = Field(
        default=None,
        description=(
            "Comma-separated string of classification(s) to filter for candidates "
            "matching that/those classification(s)."
        ),
    )
    classificationsReject: list[str] | None = Field(
        default=None,
        description=(
            "Comma-separated string of classification(s) to filter OUT candidates "
            "matching with any of those classification(s)."
        ),
    )
    minRedshift: float | None = Field(
        default=None,
        description=(
            "If provided, return only candidates with a redshift of at least this value"
        ),
    )
    maxRedshift: float | None = Field(
        default=None,
        description=(
            "If provided, return only candidates with a redshift of at most this value"
        ),
    )
    listName: str | None = Field(
        default=None,
        description=(
            'Get only candidates saved to the querying user\'s list, e.g., "favorites".'
        ),
    )
    listNameReject: str | None = Field(
        default=None,
        description=(
            "Get only candidates that ARE NOT saved to the querying user's list, "
            'e.g., "rejected_candidates".'
        ),
    )
    photometryAnnotationsFilter: list[str] | None = Field(
        default=None,
        description=(
            'Comma-separated string of "annotation: value: operator" triplet(s) to '
            "filter for sources matching that/those photometry annotation(s), "
            'i.e. "drb: 0.5: lt"'
        ),
    )
    photometryAnnotationsFilterOrigin: list[str] | None = Field(
        default=None,
        description=(
            "Comma separated string of origins. Only photometry annotations from "
            "these origins are used when filtering with the "
            "photometryAnnotationsFilter."
        ),
    )
    photometryAnnotationsFilterBefore: str | None = Field(
        default=None,
        description=(
            "Only return sources that have photometry annotations before this "
            "UTC datetime."
        ),
    )
    photometryAnnotationsFilterAfter: str | None = Field(
        default=None,
        description=(
            "Only return sources that have photometry annotations after this "
            "UTC datetime."
        ),
    )
    photometryAnnotationsFilterMinCount: int = Field(
        default=1,
        description=(
            "Only return sources that have at least this number of photometry "
            "annotations passing the photometry annotations filtering criteria. "
            "Defaults to 1."
        ),
    )
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
        description="Cumulative probability up to which to include sources",
    )
    firstDetectionAfter: str | None = Field(
        default=None,
        description=(
            "Only return sources that were first detected after this UTC datetime."
        ),
    )
    lastDetectionBefore: str | None = Field(
        default=None,
        description=(
            "Only return sources that were last detected before this UTC datetime."
        ),
    )
    numberDetections: int | None = Field(
        default=None,
        description=(
            "Only return sources that have been detected at least this many times."
        ),
    )
    requireDetections: bool = Field(
        default=True,
        description=(
            "Require firstDetectionAfter, lastDetectionBefore, and "
            "numberDetections to be set when querying candidates in a "
            "localization. Defaults to True."
        ),
    )
    excludeForcedPhotometry: bool = Field(
        default=False,
        description=(
            "If true, ignore forced photometry when applying firstDetectionAfter, "
            "lastDetectionBefore, and numberDetections. Defaults to False."
        ),
    )
    nameOnly: bool = Field(
        default=False,
        description=(
            "Intended for frontend use only: if true (and objID is provided), "
            "return only candidate obj IDs matching the partial name in objID."
        ),
    )
    objID: str | None = Field(
        default=None,
        description=(
            "Intended for frontend use only: partial object ID used by the "
            "nameOnly autocomplete query."
        ),
    )
    queryID: str | None = Field(
        default=None,
        description=(
            "Intended for frontend use only: ID of a cached candidates query, "
            "used when paginating."
        ),
    )
    annotationExcludeOrigin: str | None = Field(
        default=None,
        description="No longer supported; an error is returned if provided.",
    )
    annotationExcludeOutdatedDate: str | None = Field(
        default=None,
        description="No longer supported; an error is returned if provided.",
    )


class CandidatePostBody(ObjBody):
    """Request body for creating new candidate(s) (one per filter)."""

    id: str = Field(description="Name of the object.")
    filter_ids: list[int] = Field(description="List of associated filter IDs")
    passed_at: str = Field(
        description="Arrow-parseable datetime string indicating when passed filter."
    )
    passing_alert_id: int | None = Field(
        None, description="ID of associated filter that created candidate"
    )


class BulkDeleteCandidatesPostBody(BaseModel):
    """Request body for bulk-deleting old, unsaved candidates."""

    model_config = ConfigDict(extra="forbid")

    maxAgeMonths: int = Field(
        6,
        description="Delete objects whose most recent candidate `passed_at` is older "
        "than this many months. Defaults to 6.",
    )
    batchSize: int = Field(
        1000,
        description="Maximum number of objects to delete in this call (deleted "
        "oldest-first). Defaults to 1000.",
    )
    dryRun: bool = Field(
        False,
        description="If true, only report how many objects would be deleted, without "
        "deleting anything. Defaults to false.",
    )


class CandidateFilterGetQuery(BaseModel):
    """Query parameters for listing candidates with their alert ids."""

    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "Candidate.passed_at >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "Candidate.passed_at <= endDate"
        ),
    )
    groupIDs: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of group IDs (e.g. "1,2"). Defaults to all of '
            "user's groups if filterIDs is not provided."
        ),
    )
    filterIDs: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of filter IDs (e.g. "1,2"). Defaults to all of '
            "user's groups' filters if groupIDs is not provided."
        ),
    )
    savedStatus: Literal[*SAVED_STATUSES] = Field(
        default="all",
        description=(
            "String indicating the saved status to filter candidate results for. "
            "Must be one of the enumerated values."
        ),
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1",
    )
    numPerPage: int = Field(
        default=25,
        description=(
            "Number of candidates to return per paginated request. Defaults to 25. "
            "Capped at 500."
        ),
    )


class ScanReportPostBody(BaseModel):
    """Request body for populating a candidate scanning report."""

    model_config = ConfigDict(extra="forbid")

    group_ids: list[int] | None = Field(
        default=None,
        description="Groups used to filter the candidates and manage the report",
    )
    passed_filters_range: dict[str, Any] | None = Field(
        default=None,
        description="Range (start_date, end_date) between which the candidates "
        "passed the filters",
    )
    saved_candidates_range: dict[str, Any] | None = Field(
        default=None,
        description="Range (start_saved_date, end_saved_date) between which the "
        "candidates were saved as sources",
    )
    passed_filters_window_hours: float | None = Field(
        default=None,
        description="Alternative to passed_filters_range: a rolling window of this "
        "many hours ending now. Ignored if passed_filters_range is given. Lets a "
        "recurring caller generate reports on a schedule.",
    )
    saved_candidates_window_hours: float | None = Field(
        default=None,
        description="Alternative to saved_candidates_range: a rolling window of this "
        "many hours ending now. Ignored if saved_candidates_range is given.",
    )
    gcn_event_dateobs: str | None = Field(
        default=None,
        description="Restrict the report to objects the crossmatch associated with "
        "this GCN event",
    )


class ScanReportGetQuery(BaseModel):
    """Query parameters for listing candidate scanning reports."""

    model_config = ConfigDict(extra="forbid")

    numPerPage: int = Field(default=10, ge=1, description="Number of items to return")
    page: int = Field(default=1, ge=1, description="Page number to return")


class ScanReportItemPatchBody(BaseModel):
    """Request body for updating a scanning report item."""

    model_config = ConfigDict(extra="forbid")

    comment: str | None = Field(default=None, description="Comment on the report item")
