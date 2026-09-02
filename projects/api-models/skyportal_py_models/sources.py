"""Response models for ``/api/sources``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

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
from skyportal_py_models.notifications import email
from skyportal_py_models.objs import ObjBody
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


class SourcePost(BaseModel):
    """Payload for saving a new source (upstream ``ObjPost``)."""

    model_config = ConfigDict(extra="forbid")

    id: str
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
    detect_photometry_count: int | None = None
    group_ids: list[int] | None = None
    refresh_source: bool | None = None
    ignore_if_in_group_ids: dict[str, list[int]] | None = None
    saver_per_group_id: dict[str, int] | None = None


class SourceGcnEventCrossmatchPost(BaseModel):
    """Payload for crossmatching a source against GCN events."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    probability: float | None = None
    before_first_detection: bool | None = Field(
        default=None, alias="beforeFirstDetection"
    )
    gcn_tag_keep: list[str] | None = Field(default=None, alias="gcnTagKeep")
    gcn_tag_remove: list[str] | None = Field(default=None, alias="gcnTagRemove")
    localization_tag_keep: list[str] | None = Field(
        default=None, alias="localizationTagKeep"
    )
    localization_tag_remove: list[str] | None = Field(
        default=None, alias="localizationTagRemove"
    )
    gcn_properties_filter: list[str] | None = Field(
        default=None, alias="gcnPropertiesFilter"
    )
    localization_properties_filter: list[str] | None = Field(
        default=None, alias="localizationPropertiesFilter"
    )


class SourceMpcQueryPost(BaseModel):
    """Payload for a Minor Planet Center crossmatch."""

    model_config = ConfigDict(extra="forbid")

    obscode: str | None = None
    date: str | None = None
    limiting_magnitude: float | None = None
    search_radius: float | None = None


class SourceNotificationPost(BaseModel):
    """Payload for sending a source notification."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    source_id: str = Field(alias="sourceId")
    group_ids: list[int] = Field(alias="groupIds")
    level: Literal["soft", "hard"]
    additional_notes: str | None = Field(default=None, alias="additionalNotes")


class ObjColorMagGetQuery(BaseModel):
    """Query parameters for getting the color and absolute magnitude of a source."""

    model_config = ConfigDict(extra="forbid")

    catalog: str | None = Field(
        default=None,
        description=(
            "Partial match to the origin, associated with a catalog cross match, "
            "from which the color-mag data should be retrieved. "
            "Default is GAIA. Ignores case and underscores."
        ),
    )
    apparentMagKey: str | None = Field(
        default=None,
        description=(
            "The key inside the cross-match which is associated "
            "with the magnitude of the color-magnitude data. "
            "Will look for parallax data in addition to this magnitude "
            "in order to calculate the absolute magnitude of the object. "
            'Default is "Mag_G". Ignores case and underscores.'
        ),
    )
    parallaxKey: str | None = Field(
        default=None,
        description=(
            "The key inside the cross-match which is associated "
            "with the parallax of the source. "
            "Will look for magnitude data in addition to this parallax "
            "in order to calculate the absolute magnitude of the object. "
            'Default is "Plx". Ignores case and underscores.'
        ),
    )
    absorptionKey: str | None = Field(
        default=None,
        description=(
            "The key inside the cross-match which is associated "
            "with the source absorption term. "
            "Will add this term to the absolute magnitude calculated "
            "from apparent magnitude and parallax. "
            'Default is "A_G". Ignores case and underscores.'
        ),
    )
    absoluteMagKey: str | None = Field(
        default=None,
        description=(
            "The key inside the cross-match which is associated "
            "with the absolute magnitude of the color-magnitude data. "
            'If given, will override the "apparentMagKey", "parallaxKey" '
            'and "absorptionKey", and takes the magnitude directly from '
            "this key in the cross match dictionary. "
            "Default is None. Ignores case and underscores."
        ),
    )
    blueMagKey: str | None = Field(
        default=None,
        description=(
            "The key inside the cross-match which is associated "
            "with the source magnitude in the shorter wavelength. "
            "Will add this term to the red magnitude to get the color. "
            'Default is "Mag_Bp". Ignores case and underscores.'
        ),
    )
    redMagKey: str | None = Field(
        default=None,
        description=(
            "The key inside the cross-match which is associated "
            "with the source magnitude in the longer wavelength. "
            "Will add this term to the blue magnitude to get the color. "
            'Default is "Mag_Rp". Ignores case and underscores.'
        ),
    )
    colorKey: str | None = Field(
        default=None,
        description=(
            "The key inside the cross-match which is associated "
            "with the color term of the color-magnitude data. "
            'If given, will override the "blueMagKey", and "redMagKey", '
            "taking the color directly from the associated dictionary value. "
            "Default is None. Ignores case and underscores."
        ),
    )


DEFAULT_SOURCES_PER_PAGE = 100


DEFAULT_AGGREGATE_POINTS = 20000


class PhotStatUpdateGetQuery(BaseModel):
    """Query parameters for counting sources with and without PhotStats."""

    model_config = ConfigDict(extra="forbid")

    createdAtStartTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, only objects "
            "that have been created after this time "
            "will be checked for missing/existing PhotStats."
        ),
    )
    createdAtEndTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, only objects "
            "that have been created before this time "
            "will be checked for missing/existing PhotStats."
        ),
    )
    quickUpdateStartTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, any object's PhotStat "
            "that has been updated (either full update or "
            "an update at insert time) after this time "
            "will be recalculated."
        ),
    )
    quickUpdateEndTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, any object's PhotStat "
            "that has been updated (either full update or "
            "an update at insert time) before this time "
            "will be recalculated."
        ),
    )
    fullUpdateStartTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, any object's PhotStat "
            "that has been fully updated after this time "
            "will be counted."
        ),
    )
    fullUpdateEndTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, any object's PhotStat "
            "that has been fully updated before this time "
            "will be counted."
        ),
    )


class PhotStatUpdatePostQuery(BaseModel):
    """Query parameters for calculating PhotStats for a batch of sources."""

    model_config = ConfigDict(extra="forbid")

    numPerPage: int = Field(
        default=DEFAULT_SOURCES_PER_PAGE,
        description="Number of sources to check for updates. Defaults to 100. Max 500.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for iterating through all sources. Defaults to 1",
    )
    createdAtStartTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, only objects "
            "that have been created after this time "
            "will be checked for missing PhotStats."
        ),
    )
    createdAtEndTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, only objects "
            "that have been created before this time "
            "will be checked for missing PhotStats."
        ),
    )


class PhotStatUpdatePatchQuery(BaseModel):
    """Query parameters for recalculating PhotStats for a batch of sources."""

    model_config = ConfigDict(extra="forbid")

    numPerPage: int = Field(
        default=DEFAULT_SOURCES_PER_PAGE,
        description="Number of sources to check for updates. Defaults to 100. Max 500.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for iterating through all sources. Defaults to 1",
    )
    createdAtStartTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, only objects "
            "that have been created after this time "
            "will be checked for missing/existing PhotStats."
        ),
    )
    createdAtEndTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, only objects "
            "that have been created before this time "
            "will be checked for missing/existing PhotStats."
        ),
    )
    quickUpdateStartTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, any object's PhotStat "
            "that has been updated (either full update or "
            "an update at insert time) after this time "
            "will be recalculated."
        ),
    )
    quickUpdateEndTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, any object's PhotStat "
            "that has been updated (either full update or "
            "an update at insert time) before this time "
            "will be recalculated."
        ),
    )
    fullUpdateStartTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, any object's PhotStat "
            "that has been fully updated after this time "
            "will be recalculated."
        ),
    )
    fullUpdateEndTime: str | None = Field(
        default=None,
        description=(
            "arrow parseable string, any object's PhotStat "
            "that has been fully updated before this time "
            "will be recalculated."
        ),
    )


class PhotStatAggregateGetQuery(BaseModel):
    """Query parameters for bulk photometry statistics."""

    model_config = ConfigDict(extra="forbid")

    xField: str | None = Field(
        default=None,
        description="PhotStat field for the x axis (see the returned `fields`).",
    )
    yField: str | None = Field(
        default=None,
        description="PhotStat field for the y axis.",
    )
    zField: str | None = Field(
        default=None,
        description="Optional PhotStat field for a third (z) axis.",
    )
    classifications: str | None = Field(
        default=None,
        description=(
            "Comma-separated classification names to down-select sources "
            "(matches any). Omit to include all accessible sources."
        ),
    )
    classificationProbThreshold: float | None = Field(
        default=None,
        description="Only count classifications at or above this probability.",
    )
    group_id: int | None = Field(
        default=None,
        description=(
            "Restrict to sources saved to this group (an alternative to "
            "classification-based selection)."
        ),
    )
    obj_ids: str | None = Field(
        default=None,
        description=(
            "Comma-separated object IDs to restrict to (an alternative to "
            "classification-based selection)."
        ),
    )
    maxMatches: int = Field(
        default=DEFAULT_AGGREGATE_POINTS,
        description=(
            "Maximum number of points to return (default 20000, capped at "
            "100000). If more match, the response is truncated."
        ),
    )


class SourceGetQuery(BaseModel):
    """Query parameters for retrieving a single source or querying sources."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "TNSname",
            "includePhotometry",
            "deduplicatePhotometry",
            "includeComments",
            "includeAnalyses",
            "includePhotometryExists",
            "includeSpectrumExists",
            "includeCommentExists",
            "includePeriodExists",
            "includeThumbnails",
            "includeDetectionStats",
            "includeLabellers",
            "includeRequested",
            "pendingOnly",
            "includeColorMagnitude",
            "includeGCNCrossmatches",
            "includeGCNNotes",
            "includeCandidates",
            "includeTags",
            "includeAssociatedObjs",
            "includeSuperObjs",
        }
    )

    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1",
    )
    numPerPage: int = Field(
        default=DEFAULT_SOURCES_PER_PAGE,
        description=(
            "Number of sources to return per paginated request. Defaults to 100. "
            "Max 500."
        ),
    )
    TNSname: str | None = Field(
        default=None,
        description="TNS name for the source",
    )
    ra: str | None = Field(
        default=None,
        description="RA for spatial filtering (in decimal degrees)",
    )
    dec: str | None = Field(
        default=None,
        description="Declination for spatial filtering (in decimal degrees)",
    )
    radius: str | None = Field(
        default=None,
        description=(
            "Radius for spatial filtering if ra & dec are provided (in decimal degrees)"
        ),
    )
    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "PhotStat.first_detected_mjd >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "PhotStat.last_detected_mjd <= endDate"
        ),
    )
    detectedWindowStart: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). With requireDetections, "
            "keep sources detected during [detectedWindowStart, detectedWindowEnd] "
            "rather than sources whose whole detection history falls in the range, "
            "which is what startDate/endDate ask for. Approximated from the first "
            "and last detection, the only ones PhotStat records."
        ),
    )
    detectedWindowEnd: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). See detectedWindowStart."
        ),
    )
    listName: str | None = Field(
        default=None,
        description=(
            'Get only sources saved to the querying user\'s list, e.g., "favorites".'
        ),
    )
    sourceID: str | None = Field(
        default=None,
        description="Portion of ID or TNS name to filter on",
    )
    rejectedSourceIDs: list[str] | None = Field(
        default=None,
        description=(
            "Comma-separated string of object IDs not to be returned, useful in "
            "cases where you are looking for new sources passing a query."
        ),
    )
    includePhotometry: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated photometry. "
            "Defaults to false."
        ),
    )
    deduplicatePhotometry: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to deduplicate photometry. Defaults to false."
        ),
    )
    includeColorMagnitude: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include the color-magnitude data from "
            "Gaia. This will only include data for objects that have an annotation "
            "with the appropriate format: an annotation that contains a dictionary "
            "with keys named Mag_G, Mag_Bp, Mag_Rp, and Plx (underscores and case "
            "are ignored when matching all the above keys). The result is saved in "
            "a field named 'color_magnitude'. If no data is available, returns an "
            "empty array. Defaults to false (do not search for nor include this "
            "info)."
        ),
    )
    includeRequested: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include requested saves. Defaults to false."
        ),
    )
    includeThumbnails: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated thumbnails. "
            "Defaults to false."
        ),
    )
    pendingOnly: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to only include requested/pending saves. "
            "Defaults to false."
        ),
    )
    savedAfter: str | None = Field(
        default=None,
        description="Only return sources that were saved after this UTC datetime.",
    )
    savedBefore: str | None = Field(
        default=None,
        description="Only return sources that were saved before this UTC datetime.",
    )
    savedByCurrentUser: bool = Field(
        default=False,
        description="Only return sources that were saved by the requesting user.",
    )
    saveSummary: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to only return the source save information "
            "in the response (defaults to false). If true, the response will "
            "contain a list of dicts with the source save fields (group_id, "
            "saved_by_id, saved_at, requested, unsaved_at, obj_id, active, "
            "unsaved_by_id, created_at, modified) under "
            "`response['data']['sources']`."
        ),
    )
    sortBy: str | None = Field(
        default=None,
        description=(
            'The field to sort by. Allowed options are ["id", "alias", "origin", '
            '"ra", "dec", "redshift", "saved_at", "gcn_status", "favorites"], '
            '"altdata.<field>" to sort on an altdata field, or '
            '"annotation.<origin>.<key>" to sort on an annotation value.'
        ),
    )
    sortOrder: str = Field(
        default="desc",
        description='The sort order - either "asc" or "desc". Defaults to "desc"',
    )
    includeComments: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include comment metadata in response. "
            "Defaults to false."
        ),
    )
    includeAnalyses: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated analyses. "
            "Defaults to false."
        ),
    )
    includePhotometryExists: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return if a source has any photometry "
            "points. Defaults to false."
        ),
    )
    includeSpectrumExists: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return if a source has a spectra. "
            "Defaults to false."
        ),
    )
    includeCommentExists: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return if a source has a comment. "
            "Defaults to false."
        ),
    )
    includePeriodExists: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return if a source has a period set. "
            "Defaults to false."
        ),
    )
    includeLabellers: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return list of users who have labelled "
            "this source. Defaults to false."
        ),
    )
    includeHosts: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return source host galaxies. "
            "Defaults to false."
        ),
    )
    includeGCNCrossmatches: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return the GCN events this source is "
            "spatially and temporally coincident with. Defaults to false."
        ),
    )
    includeGCNNotes: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return the notes attached to this "
            "source's GCN crossmatches. Defaults to false."
        ),
    )
    excludeForcedPhotometry: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to ignore forced photometry when applying "
            "the detection-based filters. Defaults to false."
        ),
    )
    requireDetections: bool = Field(
        default=True,
        description=(
            "Require startDate, endDate, and numberDetections to be set when "
            "querying sources in a localization. Defaults to True."
        ),
    )
    removeNested: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to remove nested output. Defaults to false."
        ),
    )
    includeDetectionStats: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include photometry detection statistics "
            "for each source (last detection and peak detection). Defaults to false."
        ),
    )
    classifications: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of "taxonomy: classification" pair(s) to filter '
            'for sources matching that/those classification(s), i.e. "Sitewide '
            'Taxonomy: Type II, Sitewide Taxonomy: AGN"'
        ),
    )
    classifications_simul: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether object must satisfy all classifications if "
            "query (i.e. an AND rather than an OR). Defaults to false."
        ),
    )
    nonclassifications: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of "taxonomy: classification" pair(s) to filter '
            'for sources NOT matching that/those classification(s), i.e. "Sitewide '
            'Taxonomy: Type II, Sitewide Taxonomy: AGN"'
        ),
    )
    classified: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return only sources with classifications. "
            "Defaults to false."
        ),
    )
    unclassified: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to reject any sources with classifications. "
            "Defaults to false."
        ),
    )
    annotationsFilter: str | None = Field(
        default=None,
        description=(
            'Comma-separated string of "annotation: value: operator" triplet(s) to '
            'filter for sources matching that/those annotation(s), i.e. "redshift: '
            '0.5: lt"'
        ),
    )
    annotationsFilterOrigin: str | None = Field(
        default=None,
        description=(
            "Comma separated string of origins. Only annotations from these origins "
            "are used when filtering with the annotationsFilter."
        ),
    )
    annotationsFilterAfter: str | None = Field(
        default=None,
        description=(
            "Only return sources that have annotations after this UTC datetime."
        ),
    )
    annotationsFilterBefore: str | None = Field(
        default=None,
        description=(
            "Only return sources that have annotations before this UTC datetime."
        ),
    )
    commentsFilter: str | None = Field(
        default=None,
        description=(
            "Comma-separated string of comment text to filter for sources matching."
        ),
    )
    commentsFilterAuthor: int | None = Field(
        default=None,
        description=(
            "ID of a comment author. Only comments from this author are used when "
            "filtering with the commentsFilter."
        ),
    )
    commentsFilterAfter: str | None = Field(
        default=None,
        description="Only return sources that have comments after this UTC datetime.",
    )
    commentsFilterBefore: str | None = Field(
        default=None,
        description="Only return sources that have comments before this UTC datetime.",
    )
    minRedshift: float | None = Field(
        default=None,
        description=(
            "If provided, return only sources with a redshift of at least this value"
        ),
    )
    maxRedshift: float | None = Field(
        default=None,
        description=(
            "If provided, return only sources with a redshift of at most this value"
        ),
    )
    minPeakMagnitude: float | None = Field(
        default=None,
        description=(
            "If provided, return only sources with a peak photometry magnitude of "
            "at least this value"
        ),
    )
    maxPeakMagnitude: float | None = Field(
        default=None,
        description=(
            "If provided, return only sources with a peak photometry magnitude of "
            "at most this value"
        ),
    )
    minLatestMagnitude: float | None = Field(
        default=None,
        description=(
            "If provided, return only sources whose latest photometry magnitude is "
            "at least this value"
        ),
    )
    maxLatestMagnitude: float | None = Field(
        default=None,
        description=(
            "If provided, return only sources whose latest photometry magnitude is "
            "at most this value"
        ),
    )
    hasSpectrum: bool = Field(
        default=False,
        description=(
            "If true, return only those matches with at least one associated spectrum"
        ),
    )
    hasNoSpectrum: bool = Field(
        default=False,
        description="If true, return only those matches with no associated spectrum",
    )
    hasSpectrumAfter: str | None = Field(
        default=None,
        description=(
            "Only return sources with a spectrum saved after this UTC datetime"
        ),
    )
    hasSpectrumBefore: str | None = Field(
        default=None,
        description=(
            "Only return sources with a spectrum saved before this UTC datetime"
        ),
    )
    hasFollowupRequest: bool = Field(
        default=False,
        description=(
            "If true, return only those matches with at least one associated "
            "followup request"
        ),
    )
    followupRequestStatus: str | None = Field(
        default=None,
        description="If provided, string to match status of followup_request against",
    )
    createdOrModifiedAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date-time string (e.g. 2020-01-01 or "
            "2020-01-01T00:00:00 or 2020-01-01T00:00:00+00:00). If provided, filter "
            "by created_at or modified > createdOrModifiedAfter"
        ),
    )
    numberDetections: int | None = Field(
        default=None,
        description=(
            "If provided, return only sources who have at least numberDetections "
            "detections."
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
            "Localization.localization_name queried from /api/localization endpoint "
            "or skymap name in GcnEvent page table."
        ),
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include sources",
    )
    localizationRejectSources: bool = Field(
        default=False,
        description="Remove sources rejected in localization. Defaults to false.",
    )
    includeSourcesInGcn: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include the sources already confirmed in "
            "the GCN event given by localizationDateobs. Defaults to false."
        ),
    )
    spatialCatalogName: str | None = Field(
        default=None,
        description=(
            "Name of spatial catalog to use. spatialCatalogEntryName must also be "
            "defined for use."
        ),
    )
    spatialCatalogEntryName: str | None = Field(
        default=None,
        description=(
            "Name of spatial catalog entry to use. spatialCatalogName must also be "
            "defined for use."
        ),
    )
    includeGeoJSON: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include associated GeoJSON. "
            "Defaults to false."
        ),
    )
    includeCandidates: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include the candidates associated with "
            "the source. Defaults to false."
        ),
    )
    includeTags: bool = Field(
        default=True,
        description=(
            "Boolean indicating whether to include the source's tags. Defaults to true."
        ),
    )
    includeAssociatedObjs: bool = Field(
        default=True,
        description=(
            "Boolean indicating whether to include associated objects (objects "
            "grouped under the same super-object). Defaults to true."
        ),
    )
    includeSuperObjs: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to aggregate the data products (comments, "
            "annotations, classifications) of every object grouped under the same "
            "super-object. Defaults to false."
        ),
    )
    useCache: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to use cached results. Defaults to false."
        ),
    )
    queryID: str | None = Field(
        default=None,
        description=(
            "String to identify query. If provided, will be used to recover previous "
            "cached results and speed up query. Defaults to None."
        ),
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="If provided, filter only sources saved to one of these group IDs.",
    )
    simbadClass: str | None = Field(
        default=None,
        description="Simbad class to filter on",
    )
    alias: str | None = Field(
        default=None,
        description="additional name for the same object",
    )
    origin: str | None = Field(
        default=None,
        description="who posted/discovered this source",
    )
    hasTNSname: bool = Field(
        default=False,
        description="If true, return only those matches with TNS names",
    )
    hasNoTNSname: bool = Field(
        default=False,
        description="If true, return only those matches without TNS names",
    )
    hasBeenLabelled: bool = Field(
        default=False,
        description="If true, return only those objects which have been labelled",
    )
    hasNotBeenLabelled: bool = Field(
        default=False,
        description="If true, return only those objects which have not been labelled",
    )
    currentUserLabeller: bool = Field(
        default=False,
        description=(
            "If true and one of hasBeenLabelled or hasNotBeenLabelled is true, "
            "return only those objects which have been labelled/not labelled by the "
            "current user. Otherwise, return results for all users."
        ),
    )


class SourcePostBody(ObjBody):
    """Request body for saving a new (or existing) source."""

    id: str = Field(description="Name of the object.")
    group_ids: list[int] | None = Field(
        None,
        description="List of associated group IDs. If not specified, all of the "
        "user or token's groups will be used.",
    )
    refresh_source: bool = Field(
        True, description="Refresh source upon post. Defaults to True."
    )
    ignore_if_in_group_ids: dict | None = Field(
        None,
        description="Dict mapping a group_id to a list of group_ids; saving to the "
        "key group is skipped if an active source already exists in one of the "
        "listed groups. Ignored when creating a new object.",
    )
    saver_per_group_id: dict | None = Field(
        None,
        description="Admin-only. Dict mapping group_ids to the user_ids to record as "
        "the saver for that group. Defaults to the requesting user.",
    )


class SourcePatchBody(ObjBody):
    """Request body for updating an existing source (obj_id comes from the path)."""


class SourceDeleteBody(BaseModel):
    """Request body for unsaving a source from a group."""

    model_config = ConfigDict(extra="forbid")

    group_id: int | None = Field(
        None, description="ID of the group to unsave the source from."
    )


class SourceNotificationPostBody(BaseModel):
    """Request body for sending a source notification."""

    model_config = ConfigDict(extra="forbid")

    groupIds: list[int] = Field(
        description="List of IDs of groups whose members should get the notification "
        "(if they've opted in)"
    )
    sourceId: str = Field(
        description="The ID of the Source's Obj the notification is being sent about"
    )
    level: Literal["soft", "hard"] = Field(
        description="Determines whether to send an email or email+SMS notification"
    )
    additionalNotes: str | None = Field(
        None, description="Notes to append to the message sent out"
    )


class SurveyThumbnailPostBody(BaseModel):
    """Request body for adding survey thumbnails to one or more objects."""

    model_config = ConfigDict(extra="forbid")

    objID: str | None = Field(None, description="ID of the object to add thumbnails to")
    objIDs: list[str] | None = Field(
        None, description="List of object IDs to add thumbnails to"
    )
    types: list[str] | None = Field(
        None,
        description="Survey thumbnail types to add. Must be a subset of the "
        "configured default and on-demand types. Defaults to the configured "
        "default types.",
    )


class SourceObservabilityPlotGetQuery(BaseModel):
    """Query parameters for a source's observability plot."""

    model_config = ConfigDict(extra="forbid")

    maxAirmass: float = Field(
        default=2.5,
        description="Maximum airmass to consider. Defaults to 2.5.",
    )
    twilight: Literal["astronomical", "nautical", "civil"] = Field(
        default="astronomical",
        description=(
            "Twilight definition. Choices are astronomical (-18 degrees), nautical "
            "(-12 degrees), and civil (-6 degrees)."
        ),
    )


class SourceCopyPhotometryPostBody(BaseModel):
    """Request body for copying photometry from one source to another."""

    model_config = ConfigDict(extra="forbid")

    group_ids: list[int] = Field(
        description="List of IDs of groups to give photometry access to"
    )
    origin_id: str = Field(
        description="The ID of the Source's Obj the photometry is being copied from"
    )


class SourceExistsGetQuery(BaseModel):
    """Query parameters for checking whether a source already exists."""

    model_config = ConfigDict(extra="forbid")

    ra: float | None = Field(
        default=None,
        description="RA for spatial filtering (in decimal degrees)",
    )
    dec: float | None = Field(
        default=None,
        description="Declination for spatial filtering (in decimal degrees)",
    )
    radius: float | None = Field(
        default=None,
        description="Radius for spatial filtering if ra & dec are provided (in decimal degrees)",
    )


class SourceInterestPostBody(BaseModel):
    """Request body for registering an interest in a source."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Title of the planned work")
    description: str | None = Field(
        default=None, description="Description of the planned work"
    )
    link: str | None = Field(
        default=None, description="Link to a related page or document"
    )


class SourceLabelsPostBody(BaseModel):
    """Request body for labelling a source."""

    model_config = ConfigDict(extra="forbid")

    groupIds: list[int] = Field(
        description="List of IDs of groups to indicate labelling for"
    )


class SourceLabelsDeleteBody(BaseModel):
    """Request body for deleting source labels."""

    model_config = ConfigDict(extra="forbid")

    groupIds: list[int] = Field(
        description="List of IDs of groups to indicate scanning for"
    )
