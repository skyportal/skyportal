"""Response models for ``/api/candidates``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.annotations import AnnotationResponse
from skyportal_py_models.classifications import ClassificationResponse
from skyportal_py_models.comments import CommentResponse
from skyportal_py_models.galaxies import GalaxyResponse
from skyportal_py_models.groups import GroupResponse
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
