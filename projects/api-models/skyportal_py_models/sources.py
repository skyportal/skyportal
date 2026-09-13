"""Response models for ``/api/sources``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.analysis import ObjAnalysisResponse
from skyportal_py_models.annotations import AnnotationResponse
from skyportal_py_models.assignments import AssignmentResponse
from skyportal_py_models.candidates import CandidateRecordResponse
from skyportal_py_models.classifications import ClassificationResponse
from skyportal_py_models.comments import CommentResponse
from skyportal_py_models.filters import FilterResponse
from skyportal_py_models.followup_requests import FollowupRequestResponse
from skyportal_py_models.galaxies import GalaxyResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.photometry import PhotometryPointResponse
from skyportal_py_models.tags import ObjTagResponse
from skyportal_py_models.thumbnails import ThumbnailResponse
from skyportal_py_models.users import UserResponse


class PhotStatResponse(BaseModel):
    """Aggregate photometry statistics for one object (a ``PhotStat`` row)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    last_update: datetime | None = None
    last_full_update: datetime | None = None
    # Not a column: set on the instance by PhotStatHandler.get.
    last_phot_add_time: datetime | None = None
    obj_id: str | None = None
    num_obs_global: int | None = None
    num_obs_per_filter: dict[str, Any] | None = None
    num_det_global: int | None = None
    num_det_no_forced_phot_global: int | None = None
    num_det_per_filter: dict[str, Any] | None = None
    first_detected_mjd: float | None = None
    first_detected_mag: float | None = None
    first_detected_filter: str | None = None
    last_detected_mjd: float | None = None
    last_detected_mag: float | None = None
    last_detected_filter: str | None = None
    first_detected_no_forced_phot_mjd: float | None = None
    first_detected_no_forced_phot_mag: float | None = None
    first_detected_no_forced_phot_filter: str | None = None
    last_detected_no_forced_phot_mjd: float | None = None
    last_detected_no_forced_phot_mag: float | None = None
    last_detected_no_forced_phot_filter: str | None = None
    recent_obs_mjd: float | None = None
    predetection_mjds: list[float] | None = None
    last_non_detection_mjd: float | None = None
    time_to_non_detection: float | None = None
    mean_mag_global: float | None = None
    mean_mag_per_filter: dict[str, Any] | None = None
    mean_color: dict[str, Any] | None = None
    peak_mjd_global: float | None = None
    peak_mjd_per_filter: dict[str, Any] | None = None
    peak_mag_global: float | None = None
    peak_mag_per_filter: dict[str, Any] | None = None
    faintest_mag_global: float | None = None
    faintest_mag_per_filter: dict[str, Any] | None = None
    deepest_limit_global: float | None = None
    deepest_limit_per_filter: dict[str, Any] | None = None
    rise_rate: float | None = None
    decay_rate: float | None = None
    mag_rms_global: float | None = None
    mag_rms_per_filter: dict[str, Any] | None = None


class PhotStatCountsResponse(BaseModel):
    """Counts of objects with and without photometry statistics."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    total_with_phot_stats: int = Field(alias="totalWithPhotStats")
    total_without_phot_stats: int = Field(alias="totalWithoutPhotStats")


class PhotStatsBatchResponse(BaseModel):
    """Pagination summary of a batch photometry-statistics update."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    total_matches: int = Field(alias="totalMatches")
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)


class PhotStatAggregateFieldResponse(BaseModel):
    """A photometry-statistics field that can be plotted."""

    model_config = ConfigDict(extra="forbid")

    value: str
    label: str | None = None


class PhotStatAggregatePointResponse(BaseModel):
    """One source's photometry statistics, ready for plotting."""

    model_config = ConfigDict(extra="forbid")

    id: str
    ra: float | None = None
    dec: float | None = None
    redshift: float | None = None
    classification: str | None = None
    first_detected_mjd: float | None = None
    peak_mjd: float | None = None
    tns_discovery_date: str | None = None
    x: float | None = None
    y: float | None = None
    # only present when a zField was requested
    z: float | None = None


class PhotStatAggregateResponse(BaseModel):
    """Bulk photometry statistics across many sources."""

    model_config = ConfigDict(extra="forbid")

    fields: list[PhotStatAggregateFieldResponse] = Field(default_factory=list)
    points: list[PhotStatAggregatePointResponse] = Field(default_factory=list)
    count: int = 0
    truncated: bool = False


class SourceSavedGroupResponse(GroupResponse):
    """A group a source is saved to, with its ``sources`` join-table record."""

    active: bool | None = None
    requested: bool | None = None
    saved_at: datetime | None = None
    saved_by: UserResponse | None = None


class SourceDuplicateResponse(BaseModel):
    """Another saved source within 4 arcsec of this one (an ``Obj``)."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    ra: float | None = None
    dec: float | None = None
    separation: float | None = None


class SourceAssociatedObjResponse(BaseModel):
    """An object linked to this source through a ``SuperObj``."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    ra: float | None = None
    dec: float | None = None
    separation: float | None = None
    super_obj_id: int | None = None
    super_obj_name: str | None = None


GcnNoteStatus = Literal["highlighted", "rejected", "ambiguous", "pending", "not vetted"]


class SourceGcnNoteResponse(BaseModel):
    """A source's vetting note for one GCN event (a ``GcnEventObj``)."""

    model_config = ConfigDict(extra="forbid")

    dateobs: datetime | None = None
    explanation: str | None = None
    notes: str | None = None
    status: GcnNoteStatus | None = None


class SourceCandidateResponse(CandidateRecordResponse):
    """A filter passage as returned on a source (a ``Candidate``)."""

    filter: FilterResponse | None = None


class SourceFollowupRequestResponse(FollowupRequestResponse):
    """A follow-up request as returned on a source."""

    # get_source replaces the transaction rows with the decoded JSON bodies of
    # their responses, and only for admins.
    transactions: list[Any] = Field(default_factory=list)


class SourceColorMagResponse(BaseModel):
    """A color and absolute magnitude derived from one catalog cross-match."""

    model_config = ConfigDict(extra="forbid")

    origin: str | None = None
    color: float | None = None
    abs_mag: float | None = None


class SourceResponse(BaseModel):
    """A SkyPortal source (an ``Obj`` saved to at least one group)."""

    model_config = ConfigDict(extra="forbid")

    # -- Mapper columns of Obj -----------------------------------------------
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
    # Obj.to_dict strips this; the source handlers add it back by hand.
    internal_key: str | None = None

    # -- Values the handlers compute and inject -------------------------------
    gal_lat: float | None = None
    gal_lon: float | None = None
    luminosity_distance: float | None = None
    dm: float | None = None
    angular_diameter_distance: float | None = None
    ebv: float | None = None
    first_detected: datetime | None = None
    last_detected: datetime | None = None
    host_offset: float | None = None
    host_distance: float | None = None
    # period_exists on a single source, period in a sources listing.
    period_exists: bool | None = None
    period: bool | None = None
    photometry_exists: bool | None = None
    spectrum_exists: bool | None = None
    comment_exists: bool | None = None
    # Names of galaxies within 10 arcsec; None for moving objects.
    galaxies: list[str] | None = None
    duplicates: list[SourceDuplicateResponse] = Field(default_factory=list)
    associated_objs: list[SourceAssociatedObjResponse] = Field(default_factory=list)
    color_magnitude: list[SourceColorMagResponse] = Field(default_factory=list)
    gcn_notes: list[SourceGcnNoteResponse] = Field(default_factory=list)
    tags: list[ObjTagResponse] = Field(default_factory=list)

    # -- Nested records ------------------------------------------------------
    groups: list[SourceSavedGroupResponse] = Field(default_factory=list)
    thumbnails: list[ThumbnailResponse] = Field(default_factory=list)
    photstats: list[PhotStatResponse] = Field(default_factory=list)
    annotations: list[AnnotationResponse] = Field(default_factory=list)
    classifications: list[ClassificationResponse] = Field(default_factory=list)
    comments: list[CommentResponse] = Field(default_factory=list)
    photometry: list[PhotometryPointResponse] = Field(default_factory=list)
    host: GalaxyResponse | None = None
    followup_requests: list[SourceFollowupRequestResponse] = Field(default_factory=list)
    assignments: list[AssignmentResponse] = Field(default_factory=list)
    analyses: list[ObjAnalysisResponse] = Field(default_factory=list)
    candidates: list[SourceCandidateResponse] = Field(default_factory=list)
    # GcnEvent rows with an added dateobs_mjd; typed as dict to avoid an import
    # cycle with gcn_events
    gcn_crossmatch: list[dict[str, Any]] = Field(default_factory=list)
    # Users on a single source, SourceLabel rows in a sources listing.
    labellers: list[dict[str, Any]] = Field(default_factory=list)


class SourcesPageResponse(BaseModel):
    """One page of results from a sources query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    sources: list[SourceResponse]
    total_matches: int = Field(alias="totalMatches")
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)
    # Echoed back when exactly one group was queried for.
    group_id: int | None = None
    # Returned when useCache is set; pass it back to replay the query.
    query_id: str | None = Field(alias="queryID", default=None)
    geojson: dict[str, Any] | None = None


class SavedSourceResponse(BaseModel):
    """A row of the save-summary form of the sources query: the ``Source``
    join-table record between an object and the group it is saved to."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str
    group_id: int | None = None
    saved_by_id: int | None = None
    saved_at: datetime | None = None
    active: bool | None = None
    requested: bool | None = None
    unsaved_by_id: int | None = None
    unsaved_at: datetime | None = None


class SourcesSaveSummaryPageResponse(BaseModel):
    """One page of results from a save-summary sources query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    sources: list[SavedSourceResponse] = Field(default_factory=list)
    total_matches: int | None = Field(alias="totalMatches", default=None)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)
    group_id: int | None = None
    query_id: str | None = Field(alias="queryID", default=None)


class SourcePostResponse(BaseModel):
    """Result of saving a new source."""

    model_config = ConfigDict(extra="forbid")

    id: str
    saved_to_groups: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SourceOffsetStarResponse(BaseModel):
    """One line of an offset-star starlist."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    line: str = Field(alias="str")
    name: str | None = None
    ra: float | None = None
    dec: float | None = None
    dras: str | None = None
    ddecs: str | None = None
    mag: float | None = None
    pa: float | None = None


class SourceOffsetsResponse(BaseModel):
    """Offset stars for a source, in a facility's starlist format."""

    model_config = ConfigDict(extra="forbid")

    facility: str | None = None
    starlist_str: str | None = None
    starlist_info: list[SourceOffsetStarResponse] = Field(default_factory=list)
    ra: float | None = None
    dec: float | None = None
    noffsets: int | None = None
    queries_issued: int | None = None
    query: str | None = None
    used_ztfref: bool | None = None
    gaia_available: bool | None = None


class SourceFinderChartResponse(BaseModel):
    """A finding chart returned as JSON rather than as a file.

    public_url is only present when the chart was cached.
    """

    model_config = ConfigDict(extra="forbid")

    finding_chart: str
    starlist: list[SourceOffsetStarResponse] = Field(default_factory=list)
    public_url: str | None = None
    public_url_expires_at: datetime | None = None


class FinderChartFacilityResponse(BaseModel):
    """Default offset-star parameters for one finding-chart facility."""

    model_config = ConfigDict(extra="forbid")

    radius_degrees: float | None = None
    mag_limit: float | None = None
    mag_min: float | None = None
    min_sep_arcsec: float | None = None


class SourceNotificationPostResponse(BaseModel):
    """Result of sending a source notification."""

    model_config = ConfigDict(extra="forbid")

    id: int


class SourceExistsResponse(BaseModel):
    """Whether a source already exists by name or by position."""

    model_config = ConfigDict(extra="forbid")

    source_exists: bool
    message: str | None = None
