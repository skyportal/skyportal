"""Typed endpoint functions for ``/api/sources``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models.annotations import AnnotationResponse
from skyportal_py_models.gcn_events import SourceResponse
from skyportal_py_models.sources import (
    FinderChartFacilityResponse,
    GcnNoteStatus,
    PhotStatAggregateFieldResponse,
    PhotStatAggregatePointResponse,
    PhotStatAggregateResponse,
    PhotStatCountsResponse,
    PhotStatResponse,
    PhotStatsBatchResponse,
    SavedSourceResponse,
    SourceAssociatedObjResponse,
    SourceCandidateResponse,
    SourceColorMagResponse,
    SourceDuplicateResponse,
    SourceExistsResponse,
    SourceFinderChartResponse,
    SourceFollowupRequestResponse,
    SourceGcnEventCrossmatchPost,
    SourceGcnNoteResponse,
    SourceMpcQueryPost,
    SourceNotificationPost,
    SourceNotificationPostResponse,
    SourceOffsetsResponse,
    SourceOffsetStarResponse,
    SourcePost,
    SourcePostResponse,
    SourceSavedGroupResponse,
    SourcesPageResponse,
    SourcesSaveSummaryPageResponse,
)

from skyportal_py._http import unwrap, unwrap_content

__all__ = [
    "AnnotationResponse",
    "FinderChartFacilityResponse",
    "GcnNoteStatus",
    "PhotStatAggregateFieldResponse",
    "PhotStatAggregatePointResponse",
    "PhotStatAggregateResponse",
    "PhotStatCountsResponse",
    "PhotStatResponse",
    "PhotStatsBatchResponse",
    "SavedSourceResponse",
    "SourceAssociatedObjResponse",
    "SourceCandidateResponse",
    "SourceColorMagResponse",
    "SourceDuplicateResponse",
    "SourceExistsResponse",
    "SourceFinderChartResponse",
    "SourceFollowupRequestResponse",
    "SourceGcnEventCrossmatchPost",
    "SourceGcnNoteResponse",
    "SourceMpcQueryPost",
    "SourceNotificationPost",
    "SourceNotificationPostResponse",
    "SourceOffsetStarResponse",
    "SourceOffsetsResponse",
    "SourcePost",
    "SourcePostResponse",
    "SourceResponse",
    "SourceSavedGroupResponse",
    "SourcesPageResponse",
    "SourcesSaveSummaryPageResponse",
]

"""How a source stands against a GCN event, as the source handler words it."""


def fetch_source(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    obj_id: str,
    *,
    tns_name: str | None = None,
    include_thumbnails: bool = False,
    include_photometry: bool = False,
    include_color_magnitude: bool = False,
    include_photometry_exists: bool = False,
    include_spectrum_exists: bool = False,
    include_comment_exists: bool = False,
    include_detection_stats: bool = False,
    include_period_exists: bool = False,
    include_labellers: bool = False,
    include_gcn_crossmatches: bool = False,
    include_gcn_notes: bool = False,
    include_analyses: bool = False,
    include_comments: bool = False,
    include_candidates: bool = False,
    include_tags: bool = True,
    include_associated_objs: bool = True,
    include_super_objs: bool = False,
    include_requested: bool = False,
    pending_only: bool = False,
    deduplicate_photometry: bool = False,
) -> SourceResponse:
    """Retrieve a single source by object ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source, e.g. ``"ZTF20abcdef"``.
    tns_name : str, optional
        Additionally require the source to carry this TNS name (with or
        without the space, e.g. ``"2024 abc"``).
    include_thumbnails : bool, optional
        Include thumbnail data in the response.
    include_photometry : bool, optional
        Include the source's photometry in ``photometry``.
    include_color_magnitude : bool, optional
        Include the source's color/absolute-magnitude data in
        ``color_magnitude``.
    include_photometry_exists : bool, optional
        Include whether any photometry exists, in ``photometry_exists``.
    include_spectrum_exists : bool, optional
        Include whether any spectrum exists, in ``spectrum_exists``.
    include_comment_exists : bool, optional
        Include whether any comment exists, in ``comment_exists``.
    include_detection_stats : bool, optional
        Include the aggregate photometry statistics in ``photstats``.
    include_period_exists : bool, optional
        Include whether a period annotation exists, in ``period_exists``.
    include_labellers : bool, optional
        Include the users who labelled the source, in ``labellers``.
    include_gcn_crossmatches : bool, optional
        Include the source's GCN event crossmatches, in ``gcn_crossmatch``.
    include_gcn_notes : bool, optional
        Include the source's GCN vetting notes, in ``gcn_notes``.
    include_analyses : bool, optional
        Include the source's analyses in ``analyses``.
    include_comments : bool, optional
        Include the source's comments in ``comments``.
    include_candidates : bool, optional
        Include the source's filter passages in ``candidates``.
    include_tags : bool, optional
        Include the source's tags in ``tags``. Defaults to True, matching
        the server.
    include_associated_objs : bool, optional
        Include the objects linked through a SuperObjResponse in
        ``associated_objs``. Defaults to True, matching the server.
    include_super_objs : bool, optional
        Aggregate data from every object linked through the source's
        SuperObjResponse (see ``associated_objs``).
    include_requested : bool, optional
        Also include groups whose save is only requested, in ``groups``.
    pending_only : bool, optional
        Only include groups whose save is requested but not yet active.
    deduplicate_photometry : bool, optional
        With ``include_photometry``, drop photometry points duplicated
        within a short time window.
    """
    params: dict[str, str | bool] = {
        "includeThumbnails": include_thumbnails,
        "includePhotometry": include_photometry,
        "includeColorMagnitude": include_color_magnitude,
        "includePhotometryExists": include_photometry_exists,
        "includeSpectrumExists": include_spectrum_exists,
        "includeCommentExists": include_comment_exists,
        "includeDetectionStats": include_detection_stats,
        "includePeriodExists": include_period_exists,
        "includeLabellers": include_labellers,
        "includeGCNCrossmatches": include_gcn_crossmatches,
        "includeGCNNotes": include_gcn_notes,
        "includeAnalyses": include_analyses,
        "includeComments": include_comments,
        "includeCandidates": include_candidates,
        "includeTags": include_tags,
        "includeAssociatedObjs": include_associated_objs,
        "includeSuperObjs": include_super_objs,
        "includeRequested": include_requested,
        "pendingOnly": pending_only,
        "deduplicatePhotometry": deduplicate_photometry,
    }
    if tns_name is not None:
        params["TNSname"] = tns_name
    response = client.get(f"/api/sources/{obj_id}", params=params)
    return SourceResponse.model_validate(unwrap(response))


def source_exists(client: httpx.Client, obj_id: str) -> bool:
    """Check whether a source with this object ID is accessible.

    Uses the endpoint's HEAD form, which carries no body.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID to check.
    """
    return client.head(f"/api/sources/{obj_id}").is_success


def fetch_sources(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 100,
    source_id: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    radius: float | None = None,
    group_ids: list[int] | None = None,
    spatial_catalog_name: str | None = None,
    spatial_catalog_entry_name: str | None = None,
    localization_dateobs: str | None = None,
    localization_name: str | None = None,
    localization_cumprob: float | None = None,
    localization_reject_sources: bool | None = None,
    include_sources_in_gcn: bool | None = None,
    remove_nested: bool | None = None,
    list_name: str | None = None,
    saved_before: str | None = None,
    saved_after: str | None = None,
    saved_by_current_user: bool | None = None,
    include_requested: bool | None = None,
    pending_only: bool | None = None,
    created_or_modified_after: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    number_detections: int | None = None,
    exclude_forced_photometry: bool | None = None,
    require_detections: bool | None = None,
    has_spectrum: bool | None = None,
    has_no_spectrum: bool | None = None,
    has_spectrum_before: str | None = None,
    has_spectrum_after: str | None = None,
    has_tns_name: bool | None = None,
    has_no_tns_name: bool | None = None,
    has_followup_request: bool | None = None,
    followup_request_status: str | None = None,
    has_been_labelled: bool | None = None,
    has_not_been_labelled: bool | None = None,
    current_user_labeller: bool | None = None,
    simbad_class: str | None = None,
    alias: str | None = None,
    origin: str | None = None,
    classifications: list[str] | None = None,
    classifications_simul: bool | None = None,
    nonclassifications: list[str] | None = None,
    classified: bool | None = None,
    unclassified: bool | None = None,
    min_redshift: float | None = None,
    max_redshift: float | None = None,
    min_peak_magnitude: float | None = None,
    max_peak_magnitude: float | None = None,
    min_latest_magnitude: float | None = None,
    max_latest_magnitude: float | None = None,
    annotations_filter: str | None = None,
    annotations_filter_origin: str | None = None,
    annotations_filter_before: str | None = None,
    annotations_filter_after: str | None = None,
    comments_filter: str | None = None,
    comments_filter_author: int | None = None,
    comments_filter_before: str | None = None,
    comments_filter_after: str | None = None,
    rejected_source_ids: list[str] | None = None,
    include_hosts: bool | None = None,
    include_spectrum_exists: bool | None = None,
    include_comment_exists: bool | None = None,
    include_geojson: bool | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    use_cache: bool | None = None,
    query_id: str | None = None,
) -> SourcesPageResponse:
    """Query saved sources, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls.
    source_id : str, optional
        Keep sources whose object ID contains this (partial-match) string.
    ra, dec, radius : float, optional
        Cone-search filter, all in degrees; provide all three together.
    group_ids : list of int, optional
        Restrict to sources saved to these groups.
    spatial_catalog_name, spatial_catalog_entry_name : str, optional
        Keep sources inside this entry of this spatial catalog; provide
        both together.
    localization_dateobs, localization_name : str, optional
        Keep sources inside a GCN localization, identified by its event
        time and map name.
    localization_cumprob : float, optional
        Cumulative probability level of the localization region to keep
        sources within.
    localization_reject_sources : bool, optional
        Drop sources rejected against the localization's GCN event.
    include_sources_in_gcn : bool, optional
        Also keep sources already confirmed in the localization's GCN
        event, even outside the probability region.
    remove_nested : bool, optional
        Strip the nested ``thumbnails``/``annotations``/``groups`` payloads
        from each source.
    list_name : str, optional
        Keep only sources on this list of the token's user, e.g.
        ``"favorites"``.
    saved_before, saved_after : str, optional
        Keep sources saved in this ISO-format (UTC) time range.
    saved_by_current_user : bool, optional
        Keep only sources the token's user saved.
    include_requested : bool, optional
        Also keep sources whose group save is only requested.
    pending_only : bool, optional
        Keep only sources whose group save is requested but not active.
    created_or_modified_after : str, optional
        Keep sources created or modified after this ISO-format time.
    start_date, end_date : str, optional
        Keep sources last detected in this ISO-format time range.
    number_detections : int, optional
        Keep only sources with at least this many detections.
    exclude_forced_photometry : bool, optional
        Evaluate the detection-based filters against non-forced
        photometry only.
    require_detections : bool, optional
        Apply the detection-based filters, and require ``start_date``,
        ``end_date`` and ``number_detections`` when querying inside a
        localization. Defaults to True server-side.
    has_spectrum : bool, optional
        Keep only sources with at least one spectrum.
    has_no_spectrum : bool, optional
        Keep only sources without any spectrum.
    has_spectrum_before, has_spectrum_after : str, optional
        Keep sources with a spectrum observed before/after this ISO time.
    has_tns_name : bool, optional
        Keep only sources with a TNS name.
    has_no_tns_name : bool, optional
        Keep only sources without a TNS name.
    has_followup_request : bool, optional
        Keep only sources with a follow-up request.
    followup_request_status : str, optional
        With ``has_followup_request``, partial-match filter on the
        follow-up request status.
    has_been_labelled : bool, optional
        Keep only sources that have been labelled.
    has_not_been_labelled : bool, optional
        Keep only sources that have not been labelled.
    current_user_labeller : bool, optional
        With one of the labelling filters, consider only labels by the
        token's user rather than by anyone.
    simbad_class : str, optional
        Keep sources with this Simbad class.
    alias : str, optional
        Keep sources whose alias contains this (partial-match) string.
    origin : str, optional
        Keep sources whose origin contains this (partial-match) string.
    classifications, nonclassifications : list of str, optional
        Keep sources carrying / not carrying one of these
        ``"taxonomy: classification"`` strings.
    classifications_simul : bool, optional
        Require every entry of ``classifications`` to match (AND rather
        than OR).
    classified : bool, optional
        Keep only sources with at least one classification.
    unclassified : bool, optional
        Keep only sources without any classification.
    min_redshift, max_redshift : float, optional
        Redshift range filter.
    min_peak_magnitude, max_peak_magnitude : float, optional
        Peak-magnitude range filter.
    min_latest_magnitude, max_latest_magnitude : float, optional
        Latest-magnitude range filter.
    annotations_filter : str, optional
        Comma-separated ``key[:value:operator]`` annotation constraints.
    annotations_filter_origin : str, optional
        Comma-separated origins the annotations must come from.
    annotations_filter_before, annotations_filter_after : str, optional
        Keep sources with an annotation before/after this UTC datetime.
    comments_filter : str, optional
        Partial-match filter on comment text.
    comments_filter_author : int, optional
        UserResponse ID the filtered comments must be authored by.
    comments_filter_before, comments_filter_after : str, optional
        Keep sources with a comment before/after this UTC datetime.
    rejected_source_ids : list of str, optional
        Object IDs to exclude from the results.
    include_hosts : bool, optional
        Include each source's host galaxy in ``host``.
    include_spectrum_exists : bool, optional
        Include whether any spectrum exists, in ``spectrum_exists``.
    include_comment_exists : bool, optional
        Include whether any comment exists, in ``comment_exists``.
    include_geojson : bool, optional
        Include a GeoJSON representation of the page in ``geojson``.
    sort_by, sort_order : str, optional
        Sort column (a source column, ``"saved_at"``, ``"altdata.<key>"``
        or ``"annotation.<origin>.<key>"``) and direction ("asc"/"desc").
    use_cache : bool, optional
        Cache the matching IDs server-side: the first page returns a
        ``query_id`` to pass back for later pages.
    query_id : str, optional
        With ``use_cache``, replay a cached query when fetching pages
        after the first.
    """
    params: dict[str, str | int | float | bool] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        **_sources_filter_params(
            source_id=source_id,
            ra=ra,
            dec=dec,
            radius=radius,
            group_ids=group_ids,
            spatial_catalog_name=spatial_catalog_name,
            spatial_catalog_entry_name=spatial_catalog_entry_name,
            localization_dateobs=localization_dateobs,
            localization_name=localization_name,
            localization_cumprob=localization_cumprob,
            localization_reject_sources=localization_reject_sources,
            include_sources_in_gcn=include_sources_in_gcn,
            remove_nested=remove_nested,
            list_name=list_name,
            saved_before=saved_before,
            saved_after=saved_after,
            saved_by_current_user=saved_by_current_user,
            include_requested=include_requested,
            pending_only=pending_only,
            created_or_modified_after=created_or_modified_after,
            start_date=start_date,
            end_date=end_date,
            number_detections=number_detections,
            exclude_forced_photometry=exclude_forced_photometry,
            require_detections=require_detections,
            has_spectrum=has_spectrum,
            has_no_spectrum=has_no_spectrum,
            has_spectrum_before=has_spectrum_before,
            has_spectrum_after=has_spectrum_after,
            has_tns_name=has_tns_name,
            has_no_tns_name=has_no_tns_name,
            has_followup_request=has_followup_request,
            followup_request_status=followup_request_status,
            has_been_labelled=has_been_labelled,
            has_not_been_labelled=has_not_been_labelled,
            current_user_labeller=current_user_labeller,
            simbad_class=simbad_class,
            alias=alias,
            origin=origin,
            classifications=classifications,
            classifications_simul=classifications_simul,
            nonclassifications=nonclassifications,
            classified=classified,
            unclassified=unclassified,
            min_redshift=min_redshift,
            max_redshift=max_redshift,
            min_peak_magnitude=min_peak_magnitude,
            max_peak_magnitude=max_peak_magnitude,
            min_latest_magnitude=min_latest_magnitude,
            max_latest_magnitude=max_latest_magnitude,
            annotations_filter=annotations_filter,
            annotations_filter_origin=annotations_filter_origin,
            annotations_filter_before=annotations_filter_before,
            annotations_filter_after=annotations_filter_after,
            comments_filter=comments_filter,
            comments_filter_author=comments_filter_author,
            comments_filter_before=comments_filter_before,
            comments_filter_after=comments_filter_after,
            rejected_source_ids=rejected_source_ids,
            include_hosts=include_hosts,
            include_spectrum_exists=include_spectrum_exists,
            include_comment_exists=include_comment_exists,
            include_geojson=include_geojson,
            sort_by=sort_by,
            sort_order=sort_order,
            use_cache=use_cache,
            query_id=query_id,
        ),
    }
    response = client.get("/api/sources", params=params)
    return SourcesPageResponse.model_validate(unwrap(response))


_SOURCES_FILTER_WIRE_NAMES = {
    "source_id": "sourceID",
    "ra": "ra",
    "dec": "dec",
    "radius": "radius",
    "spatial_catalog_name": "spatialCatalogName",
    "spatial_catalog_entry_name": "spatialCatalogEntryName",
    "localization_dateobs": "localizationDateobs",
    "localization_name": "localizationName",
    "localization_cumprob": "localizationCumprob",
    "localization_reject_sources": "localizationRejectSources",
    "include_sources_in_gcn": "includeSourcesInGcn",
    "remove_nested": "removeNested",
    "list_name": "listName",
    "saved_before": "savedBefore",
    "saved_after": "savedAfter",
    "saved_by_current_user": "savedByCurrentUser",
    "include_requested": "includeRequested",
    "pending_only": "pendingOnly",
    "created_or_modified_after": "createdOrModifiedAfter",
    "start_date": "startDate",
    "end_date": "endDate",
    "number_detections": "numberDetections",
    "exclude_forced_photometry": "excludeForcedPhotometry",
    "require_detections": "requireDetections",
    "has_spectrum": "hasSpectrum",
    "has_no_spectrum": "hasNoSpectrum",
    "has_spectrum_before": "hasSpectrumBefore",
    "has_spectrum_after": "hasSpectrumAfter",
    "has_tns_name": "hasTNSname",
    "has_no_tns_name": "hasNoTNSname",
    "has_followup_request": "hasFollowupRequest",
    "followup_request_status": "followupRequestStatus",
    "has_been_labelled": "hasBeenLabelled",
    "has_not_been_labelled": "hasNotBeenLabelled",
    "current_user_labeller": "currentUserLabeller",
    "simbad_class": "simbadClass",
    "alias": "alias",
    "origin": "origin",
    # The server reads this one in snake_case.
    "classifications_simul": "classifications_simul",
    "classified": "classified",
    "unclassified": "unclassified",
    "min_redshift": "minRedshift",
    "max_redshift": "maxRedshift",
    "min_peak_magnitude": "minPeakMagnitude",
    "max_peak_magnitude": "maxPeakMagnitude",
    "min_latest_magnitude": "minLatestMagnitude",
    "max_latest_magnitude": "maxLatestMagnitude",
    "annotations_filter": "annotationsFilter",
    "annotations_filter_origin": "annotationsFilterOrigin",
    "annotations_filter_before": "annotationsFilterBefore",
    "annotations_filter_after": "annotationsFilterAfter",
    "comments_filter": "commentsFilter",
    "comments_filter_author": "commentsFilterAuthor",
    "comments_filter_before": "commentsFilterBefore",
    "comments_filter_after": "commentsFilterAfter",
    "include_hosts": "includeHosts",
    "include_spectrum_exists": "includeSpectrumExists",
    "include_comment_exists": "includeCommentExists",
    "include_geojson": "includeGeoJSON",
    "sort_by": "sortBy",
    "sort_order": "sortOrder",
    "use_cache": "useCache",
    "query_id": "queryID",
}


def _sources_filter_params(
    **kwargs: Any,  # noqa: ANN401 -- values are the caller's typed keyword arguments
) -> dict[str, str | int | float | bool]:
    """Map provided sources-list keyword arguments to wire query params."""
    group_ids = kwargs.pop("group_ids", None)
    classifications = kwargs.pop("classifications", None)
    nonclassifications = kwargs.pop("nonclassifications", None)
    rejected_source_ids = kwargs.pop("rejected_source_ids", None)
    params: dict[str, str | int | float | bool] = {
        _SOURCES_FILTER_WIRE_NAMES[name]: value
        for name, value in kwargs.items()
        if value is not None
    }
    if group_ids is not None:
        params["group_ids"] = ",".join(str(gid) for gid in group_ids)
    if classifications is not None:
        params["classifications"] = ",".join(classifications)
    if nonclassifications is not None:
        params["nonclassifications"] = ",".join(nonclassifications)
    if rejected_source_ids is not None:
        params["rejectedSourceIDs"] = ",".join(rejected_source_ids)
    return params


def fetch_sources_save_summary(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 100,
    group_ids: list[int] | None = None,
    saved_before: str | None = None,
    saved_after: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    use_cache: bool | None = None,
    query_id: str | None = None,
) -> SourcesSaveSummaryPageResponse:
    """Query when and by whom sources were saved, one page at a time.

    The ``saveSummary`` form of the sources query returns the save records
    (object ID, group, saver, time) instead of the objects themselves.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls.
    group_ids : list of int, optional
        Restrict to sources saved to these groups.
    saved_before, saved_after : str, optional
        Keep sources saved in this ISO-format (UTC) time range.
    sort_by, sort_order : str, optional
        Sort column (e.g. ``"saved_at"``) and direction ("asc"/"desc").
    use_cache : bool, optional
        Cache the matching IDs server-side: the first page returns a
        ``query_id`` to pass back for later pages.
    query_id : str, optional
        With ``use_cache``, replay a cached query when fetching pages
        after the first.
    """
    params: dict[str, str | int | float | bool] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "saveSummary": True,
        **_sources_filter_params(
            group_ids=group_ids,
            saved_before=saved_before,
            saved_after=saved_after,
            sort_by=sort_by,
            sort_order=sort_order,
            use_cache=use_cache,
            query_id=query_id,
        ),
    }
    response = client.get("/api/sources", params=params)
    return SourcesSaveSummaryPageResponse.model_validate(unwrap(response))


def post_source(client: httpx.Client, payload: SourcePost) -> SourcePostResponse:
    """Save a new source (or update one the token could not previously see).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : SourcePost
        The source to save. ``ra`` and ``dec`` are required for an object
        that does not exist yet; for one that does, any field given is
        applied as an update. If ``group_ids`` is omitted, the server saves
        the source to all of the token's groups.
    """
    response = client.post("/api/sources", json=payload.model_dump(exclude_none=True))
    return SourcePostResponse.model_validate(unwrap(response))


def update_source(  # noqa: PLR0913 -- mirrors the endpoint's body parameters
    client: httpx.Client,
    obj_id: str,
    *,
    ra: float | None = None,
    dec: float | None = None,
    redshift: float | None = None,
    transient: bool | None = None,
    ra_dis: float | None = None,
    altdata: dict[str, Any] | None = None,
    summary: str | None = None,
) -> None:
    """Update fields of an existing source.

    Only the provided fields are sent; omitted fields are left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source to update.
    ra, dec : float, optional
        New coordinates, in degrees.
    redshift : float, optional
        New redshift.
    transient : bool, optional
        Whether the source is an astrophysical transient.
    ra_dis, altdata : optional
        Discovery right ascension and misc. metadata stored as JSON.
    summary : str, optional
        New human-readable summary of the source.
    """
    fields = {
        "ra": ra,
        "dec": dec,
        "redshift": redshift,
        "transient": transient,
        "ra_dis": ra_dis,
        "altdata": altdata,
        "summary": summary,
    }
    payload = {name: value for name, value in fields.items() if value is not None}
    unwrap(client.patch(f"/api/sources/{obj_id}", json=payload))


def delete_source(client: httpx.Client, obj_id: str, group_id: int) -> None:
    """Unsave a source from one group.

    The source is deactivated for that group rather than deleted outright;
    the token must have access to the group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source to unsave.
    group_id : int
        GroupResponse to unsave the source from. Sent in the request body.
    """
    unwrap(
        client.request(
            "DELETE",
            f"/api/sources/{obj_id}",
            json={"group_id": group_id},
        )
    )


def delete_source_photometry(client: httpx.Client, obj_id: str) -> str:
    """Delete all of a source's photometry points.

    Requires the "Delete bulk photometry" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source whose photometry is deleted.
    """
    return str(unwrap(client.delete(f"/api/sources/{obj_id}/photometry")))


def fetch_source_offsets(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    obj_id: str,
    *,
    facility: str = "Keck",
    num_offset_stars: int = 3,
    obstime: str | None = None,
    use_ztfref: bool = True,
    observing_run_id: int | None = None,
) -> SourceOffsetsResponse:
    """Retrieve offset stars for a source, to aid in spectroscopy.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    facility : str, optional
        Starlist format, one of ``"Keck"``, ``"Shane"``, ``"P200"``, or
        ``"P200-NGPS"``. Defaults to ``"Keck"``.
    num_offset_stars : int, optional
        Number of offset stars requested, in [0, 10]. Zero returns a
        starlist of just the source. Defaults to 3.
    obstime : str, optional
        ObservationResponse time in ISO format, e.g. ``"2020-12-30T12:34:10"``.
        Defaults to now.
    use_ztfref : bool, optional
        Use the ZTFref catalog for offset-star positions instead of Gaia
        DR3. Defaults to True.
    observing_run_id : int, optional
        Observing run whose assignment priority and comment should be
        folded into the starlist.
    """
    params: dict[str, str | int | bool] = {
        "facility": facility,
        "num_offset_stars": num_offset_stars,
        "use_ztfref": use_ztfref,
    }
    if obstime is not None:
        params["obstime"] = obstime
    if observing_run_id is not None:
        params["observing_run_id"] = observing_run_id
    response = client.get(f"/api/sources/{obj_id}/offsets", params=params)
    return SourceOffsetsResponse.model_validate(unwrap(response))


def _source_finder_params(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    *,
    imsize: float,
    facility: str,
    image_source: str,
    use_ztfref: bool,
    obstime: str | None,
    output_type: str,
    num_offset_stars: int,
    mag_min: float | None,
    mag_limit: float | None,
    use_cache: bool,
) -> dict[str, str | float | int | bool]:
    params: dict[str, str | float | int | bool] = {
        "imsize": imsize,
        "facility": facility,
        "image_source": image_source,
        "use_ztfref": use_ztfref,
        "type": output_type,
        "num_offset_stars": num_offset_stars,
        "use_cache": use_cache,
    }
    if obstime is not None:
        params["obstime"] = obstime
    if mag_min is not None:
        params["mag_min"] = mag_min
    if mag_limit is not None:
        params["mag_limit"] = mag_limit
    return params


def fetch_source_finder(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    obj_id: str,
    *,
    imsize: float = 4.0,
    facility: str = "Keck",
    image_source: str = "ps1",
    use_ztfref: bool = True,
    obstime: str | None = None,
    output_type: str = "pdf",
    num_offset_stars: int = 3,
    mag_min: float | None = None,
    mag_limit: float | None = None,
    use_cache: bool = True,
) -> bytes:
    """Generate a finding chart for a source, as a PDF or PNG file.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    imsize : float, optional
        Square image size in arcmin, in [2, 15]. Defaults to 4.0.
    facility : str, optional
        Starlist format, one of ``"Keck"``, ``"Shane"``, ``"P200"``, or
        ``"P200-NGPS"``. Defaults to ``"Keck"``.
    image_source : str, optional
        Chart image source, one of ``"ps1"``, ``"desi"``, ``"dss"``, or
        ``"ztfref"``. Defaults to ``"ps1"``.
    use_ztfref : bool, optional
        Use the ZTFref catalog for offset-star positions instead of Gaia
        DR3. Defaults to True.
    obstime : str, optional
        ObservationResponse time in ISO format. Defaults to now.
    output_type : str, optional
        Output file type, ``"pdf"`` or ``"png"``. Defaults to ``"pdf"``.
    num_offset_stars : int, optional
        Number of offset stars to show, in [0, 4]. Defaults to 3.
    mag_min, mag_limit : float, optional
        Brightest and faintest offset-star magnitudes to allow. Each
        defaults to the facility value.
    use_cache : bool, optional
        Reuse a cached chart when one is available. Defaults to True.
    """
    params = _source_finder_params(
        imsize=imsize,
        facility=facility,
        image_source=image_source,
        use_ztfref=use_ztfref,
        obstime=obstime,
        output_type=output_type,
        num_offset_stars=num_offset_stars,
        mag_min=mag_min,
        mag_limit=mag_limit,
        use_cache=use_cache,
    )
    response = client.get(f"/api/sources/{obj_id}/finder", params=params)
    return unwrap_content(response)


def fetch_source_finder_json(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    obj_id: str,
    *,
    imsize: float = 4.0,
    facility: str = "Keck",
    image_source: str = "ps1",
    use_ztfref: bool = True,
    obstime: str | None = None,
    output_type: str = "pdf",
    num_offset_stars: int = 3,
    mag_min: float | None = None,
    mag_limit: float | None = None,
    use_cache: bool = True,
) -> SourceFinderChartResponse:
    """Generate a finding chart and return it as base64 JSON with its starlist.

    Same endpoint as :func:`fetch_source_finder`, called with ``as_json``.
    ``public_url`` is only present when the chart was cached.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    imsize : float, optional
        Square image size in arcmin, in [2, 15]. Defaults to 4.0.
    facility : str, optional
        Starlist format, one of ``"Keck"``, ``"Shane"``, ``"P200"``, or
        ``"P200-NGPS"``. Defaults to ``"Keck"``.
    image_source : str, optional
        Chart image source, one of ``"ps1"``, ``"desi"``, ``"dss"``, or
        ``"ztfref"``. Defaults to ``"ps1"``.
    use_ztfref : bool, optional
        Use the ZTFref catalog for offset-star positions instead of Gaia
        DR3. Defaults to True.
    obstime : str, optional
        ObservationResponse time in ISO format. Defaults to now.
    output_type : str, optional
        Chart file type, ``"pdf"`` or ``"png"``. Defaults to ``"pdf"``.
    num_offset_stars : int, optional
        Number of offset stars to show, in [0, 4]. Defaults to 3.
    mag_min, mag_limit : float, optional
        Brightest and faintest offset-star magnitudes to allow. Each
        defaults to the facility value.
    use_cache : bool, optional
        Reuse a cached chart when one is available. Defaults to True.
    """
    params = _source_finder_params(
        imsize=imsize,
        facility=facility,
        image_source=image_source,
        use_ztfref=use_ztfref,
        obstime=obstime,
        output_type=output_type,
        num_offset_stars=num_offset_stars,
        mag_min=mag_min,
        mag_limit=mag_limit,
        use_cache=use_cache,
    )
    params["as_json"] = True
    response = client.get(f"/api/sources/{obj_id}/finder", params=params)
    return SourceFinderChartResponse.model_validate(unwrap(response))


def fetch_finder_chart_facilities(
    client: httpx.Client,
) -> dict[str, FinderChartFacilityResponse]:
    """Retrieve the per-facility default finding-chart parameters.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/finder_chart/facilities")
    return {
        name: FinderChartFacilityResponse.model_validate(parameters)
        for name, parameters in unwrap(response).items()
    }


def post_source_host(client: httpx.Client, obj_id: str, galaxy_name: str) -> None:
    """Set a source's host galaxy.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    galaxy_name : str
        Name of an existing galaxy to associate with the object.
    """
    unwrap(
        client.post(
            f"/api/sources/{obj_id}/host",
            json={"galaxyName": galaxy_name},
        )
    )


def delete_source_host(client: httpx.Client, obj_id: str) -> None:
    """Clear a source's host galaxy.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    """
    unwrap(client.delete(f"/api/sources/{obj_id}/host"))


def fetch_source_saved_groups(
    client: httpx.Client, obj_id: str
) -> list[SourceSavedGroupResponse]:
    """Retrieve the groups a source is saved to or requested for.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    """
    response = client.get(f"/api/sources/{obj_id}/groups")
    return [
        SourceSavedGroupResponse.model_validate(group) for group in unwrap(response)
    ]


def post_source_labels(client: httpx.Client, obj_id: str, group_ids: list[int]) -> None:
    """Record that the calling user has labelled a source for some groups.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    group_ids : list of int
        Groups to record labelling for. Labels already present are left
        untouched.
    """
    unwrap(
        client.post(
            f"/api/sources/{obj_id}/labels",
            json={"groupIds": group_ids},
        )
    )


def delete_source_labels(
    client: httpx.Client, obj_id: str, group_ids: list[int]
) -> None:
    """Remove the calling user's labels on a source for some groups.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    group_ids : list of int
        Groups to remove labels for. Sent in the request body.
    """
    unwrap(
        client.request(
            "DELETE",
            f"/api/sources/{obj_id}/labels",
            json={"groupIds": group_ids},
        )
    )


def fetch_source_color_mag(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    obj_id: str,
    *,
    catalog: str | None = None,
    apparent_mag_key: str | None = None,
    parallax_key: str | None = None,
    absorption_key: str | None = None,
    absolute_mag_key: str | None = None,
    blue_mag_key: str | None = None,
    red_mag_key: str | None = None,
    color_key: str | None = None,
) -> list[SourceColorMagResponse]:
    """Retrieve a source's color and absolute magnitude from cross-match annotations.

    All key arguments are matched against annotation keys ignoring case and
    underscores.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    catalog : str, optional
        Partial match on the annotation origin. Defaults to ``"GAIA"``.
    apparent_mag_key : str, optional
        AnnotationResponse key holding the apparent magnitude. Defaults to
        ``"Mag_G"``.
    parallax_key : str, optional
        AnnotationResponse key holding the parallax, used with the apparent
        magnitude to derive the absolute magnitude. Defaults to ``"Plx"``.
    absorption_key : str, optional
        AnnotationResponse key holding the absorption term added to the derived
        absolute magnitude. Defaults to ``"A_G"``.
    absolute_mag_key : str, optional
        AnnotationResponse key holding the absolute magnitude directly; overrides
        ``apparent_mag_key``, ``parallax_key`` and ``absorption_key``.
    blue_mag_key, red_mag_key : str, optional
        AnnotationResponse keys differenced to form the color. Default to
        ``"Mag_Bp"`` and ``"Mag_Rp"``.
    color_key : str, optional
        AnnotationResponse key holding the color directly; overrides
        ``blue_mag_key`` and ``red_mag_key``.
    """
    params: dict[str, str] = {}
    optional = {
        "catalog": catalog,
        "apparentMagKey": apparent_mag_key,
        "parallaxKey": parallax_key,
        "absorptionKey": absorption_key,
        "absoluteMagKey": absolute_mag_key,
        "blueMagKey": blue_mag_key,
        "redMagKey": red_mag_key,
        "colorKey": color_key,
    }
    params.update(
        {name: value for name, value in optional.items() if value is not None}
    )
    response = client.get(f"/api/sources/{obj_id}/color_mag", params=params)
    return [SourceColorMagResponse.model_validate(entry) for entry in unwrap(response)]


def post_source_gcn_event_crossmatch(
    client: httpx.Client,
    obj_id: str,
    payload: SourceGcnEventCrossmatchPost,
) -> None:
    """Crossmatch a source against GCN events in a date range.

    The crossmatch runs in the background; the call returns as soon as it
    is queued. ``start_date`` and ``end_date`` are required and must be
    within 31 days of each other.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    payload : SourceGcnEventCrossmatchPost
        Date range, probability contour, and GCN/localization filters.
    """
    unwrap(
        client.post(
            f"/api/sources/{obj_id}/gcn_event",
            json=payload.model_dump(by_alias=True, exclude_none=True),
        )
    )


def post_source_mpc_query(
    client: httpx.Client,
    obj_id: str,
    payload: SourceMpcQueryPost | None = None,
) -> None:
    """Query the Minor Planet Center for known minor planets at a source's position.

    The query runs in the background; on a match the object is flagged as
    a solar system object and its MPC name and alias are stored.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    payload : SourceMpcQueryPost, optional
        Query settings. The server defaults to observatory code ``"500"``
        (geocentric), the current time, a limiting magnitude of 24.0, and a
        search radius of 1 arcmin.
    """
    body = {} if payload is None else payload.model_dump(exclude_none=True)
    unwrap(client.post(f"/api/sources/{obj_id}/mpc", json=body))


def fetch_source_tns(
    client: httpx.Client,
    obj_id: str,
    *,
    radius: float = 2.0,
) -> None:
    """Look up a source on the Transient Name Server.

    The lookup runs in the background and stores the result on the object;
    the call returns as soon as it is queued.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    radius : float, optional
        Cone-search radius in arcseconds; must be non-negative. Defaults
        to 2.0.
    """
    unwrap(client.get(f"/api/sources/{obj_id}/tns", params={"radius": radius}))


def fetch_source_observability(
    client: httpx.Client,
    obj_id: str,
    *,
    max_airmass: float = 2.5,
    twilight: str = "astronomical",
) -> bytes:
    """Generate an observability plot for a source, as a PDF file.

    The plot covers the next 24 hours for every fixed-location telescope
    the token can see.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    max_airmass : float, optional
        Maximum airmass to consider. Defaults to 2.5.
    twilight : str, optional
        Twilight definition, one of ``"astronomical"`` (-18 degrees),
        ``"nautical"`` (-12 degrees), or ``"civil"`` (-6 degrees).
        Defaults to ``"astronomical"``.
    """
    response = client.get(
        f"/api/sources/{obj_id}/observability",
        params={"maxAirmass": max_airmass, "twilight": twilight},
    )
    return unwrap_content(response)


def post_source_photometry_copy(
    client: httpx.Client,
    obj_id: str,
    origin_id: str,
    group_ids: list[int],
) -> None:
    """Copy every photometry point from one source onto another.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the target source, which the photometry is copied to.
    origin_id : str
        Object ID of the source the photometry is copied from.
    group_ids : list of int
        Groups to give access to the copied photometry.
    """
    unwrap(
        client.post(
            f"/api/sources/{obj_id}/copy_photometry",
            json={"origin_id": origin_id, "group_ids": group_ids},
        )
    )


def fetch_source_phot_stat(client: httpx.Client, obj_id: str) -> PhotStatResponse:
    """Retrieve the photometry statistics of a source.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    """
    response = client.get(f"/api/sources/{obj_id}/phot_stat")
    return PhotStatResponse.model_validate(unwrap(response))


def post_source_phot_stat(client: httpx.Client, obj_id: str) -> None:
    """Calculate and store photometry statistics for a source.

    Requires system admin permissions, and fails if statistics already
    exist for the object.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    """
    unwrap(client.post(f"/api/sources/{obj_id}/phot_stat"))


def update_source_phot_stat(client: httpx.Client, obj_id: str) -> None:
    """Recalculate a source's photometry statistics, creating them if absent.

    Requires system admin permissions.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    """
    unwrap(client.put(f"/api/sources/{obj_id}/phot_stat"))


def delete_source_phot_stat(client: httpx.Client, obj_id: str) -> None:
    """Delete a source's photometry statistics.

    Requires system admin permissions.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source.
    """
    unwrap(client.delete(f"/api/sources/{obj_id}/phot_stat"))


def fetch_phot_stats_counts(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    created_at_start_time: str | None = None,
    created_at_end_time: str | None = None,
    quick_update_start_time: str | None = None,
    quick_update_end_time: str | None = None,
    full_update_start_time: str | None = None,
    full_update_end_time: str | None = None,
) -> PhotStatCountsResponse:
    """Count the objects with and without photometry statistics.

    Requires system admin permissions.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    created_at_start_time, created_at_end_time : str, optional
        Arrow-parseable times bounding object creation.
    quick_update_start_time, quick_update_end_time : str, optional
        Arrow-parseable times bounding the last statistics update of any
        kind.
    full_update_start_time, full_update_end_time : str, optional
        Arrow-parseable times bounding the last full statistics update.
    """
    params: dict[str, str] = {}
    optional = {
        "createdAtStartTime": created_at_start_time,
        "createdAtEndTime": created_at_end_time,
        "quickUpdateStartTime": quick_update_start_time,
        "quickUpdateEndTime": quick_update_end_time,
        "fullUpdateStartTime": full_update_start_time,
        "fullUpdateEndTime": full_update_end_time,
    }
    params.update(
        {name: value for name, value in optional.items() if value is not None}
    )
    response = client.get("/api/phot_stats", params=params)
    return PhotStatCountsResponse.model_validate(unwrap(response))


def post_phot_stats(
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 100,
    created_at_start_time: str | None = None,
    created_at_end_time: str | None = None,
) -> PhotStatsBatchResponse:
    """Calculate photometry statistics for a page of objects that lack them.

    Requires system admin permissions.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls over the objects without statistics;
        ``num_per_page`` is capped server-side at 500.
    created_at_start_time, created_at_end_time : str, optional
        Arrow-parseable times bounding object creation.
    """
    params: dict[str, str | int] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if created_at_start_time is not None:
        params["createdAtStartTime"] = created_at_start_time
    if created_at_end_time is not None:
        params["createdAtEndTime"] = created_at_end_time
    response = client.post("/api/phot_stats", params=params)
    return PhotStatsBatchResponse.model_validate(unwrap(response))


def update_phot_stats(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 100,
    created_at_start_time: str | None = None,
    created_at_end_time: str | None = None,
    quick_update_start_time: str | None = None,
    quick_update_end_time: str | None = None,
    full_update_start_time: str | None = None,
    full_update_end_time: str | None = None,
) -> PhotStatsBatchResponse:
    """Recalculate photometry statistics for a page of objects that have them.

    Requires system admin permissions.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls; ``num_per_page`` is capped server-side at 500.
    created_at_start_time, created_at_end_time : str, optional
        Arrow-parseable times bounding object creation.
    quick_update_start_time, quick_update_end_time : str, optional
        Arrow-parseable times bounding the last statistics update of any
        kind.
    full_update_start_time, full_update_end_time : str, optional
        Arrow-parseable times bounding the last full statistics update.
    """
    params: dict[str, str | int] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    optional = {
        "createdAtStartTime": created_at_start_time,
        "createdAtEndTime": created_at_end_time,
        "quickUpdateStartTime": quick_update_start_time,
        "quickUpdateEndTime": quick_update_end_time,
        "fullUpdateStartTime": full_update_start_time,
        "fullUpdateEndTime": full_update_end_time,
    }
    params.update(
        {name: value for name, value in optional.items() if value is not None}
    )
    response = client.patch("/api/phot_stats", params=params)
    return PhotStatsBatchResponse.model_validate(unwrap(response))


def fetch_phot_stats_aggregate(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    x_field: str | None = None,
    y_field: str | None = None,
    z_field: str | None = None,
    classifications: list[str] | None = None,
    classification_prob_threshold: float | None = None,
    group_id: int | None = None,
    obj_ids: list[str] | None = None,
    max_matches: int | None = None,
) -> PhotStatAggregateResponse:
    """Retrieve photometry statistics across many sources, for bulk plotting.

    Called without ``x_field`` and ``y_field``, the response holds only the
    list of plottable fields.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    x_field, y_field : str, optional
        Photometry-statistics fields for the x and y axes; both are
        required to get any points back.
    z_field : str, optional
        Optional third axis.
    classifications : list of str, optional
        Restrict to sources carrying any of these classification names.
    classification_prob_threshold : float, optional
        Only count classifications at or above this probability.
    group_id : int, optional
        Restrict to sources saved to this group.
    obj_ids : list of str, optional
        Restrict to these objects.
    max_matches : int, optional
        Maximum number of points to return. Defaults to 20000 server-side
        and is capped at 100000; the response flags truncation.
    """
    params: dict[str, str | int | float] = {}
    if x_field is not None:
        params["xField"] = x_field
    if y_field is not None:
        params["yField"] = y_field
    if z_field is not None:
        params["zField"] = z_field
    if classifications is not None:
        params["classifications"] = ",".join(classifications)
    if classification_prob_threshold is not None:
        params["classificationProbThreshold"] = classification_prob_threshold
    if group_id is not None:
        params["group_id"] = group_id
    if obj_ids is not None:
        params["obj_ids"] = ",".join(obj_ids)
    if max_matches is not None:
        params["maxMatches"] = max_matches
    response = client.get("/api/phot_stats/aggregate", params=params)
    return PhotStatAggregateResponse.model_validate(unwrap(response))


def fetch_source_exists(
    client: httpx.Client,
    obj_id: str | None = None,
    *,
    ra: float | None = None,
    dec: float | None = None,
    radius: float | None = None,
) -> SourceExistsResponse:
    """Check whether a source already exists by name or by position.

    Provide ``obj_id``, or all of ``ra``, ``dec`` and ``radius``, or both:
    with both, a name match short-circuits and a position match is tried
    otherwise.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str, optional
        Object ID to look for.
    ra, dec, radius : float, optional
        Cone search in decimal degrees; provide all three together.
    """
    params: dict[str, float] = {}
    if ra is not None:
        params["ra"] = ra
    if dec is not None:
        params["dec"] = dec
    if radius is not None:
        params["radius"] = radius
    path = "/api/source_exists" if obj_id is None else f"/api/source_exists/{obj_id}"
    response = client.get(path, params=params)
    return SourceExistsResponse.model_validate(unwrap(response))


def post_source_notification(
    client: httpx.Client, payload: SourceNotificationPost
) -> SourceNotificationPostResponse:
    """Notify the members of some groups about a source.

    Requires notifications to be enabled on the deployment, and the token
    must belong to every group the source is being announced to.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : SourceNotificationPost
        SourceResponse, recipient groups, and notification level: ``"soft"`` sends
        an email, ``"hard"`` sends an email and an SMS.
    """
    response = client.post(
        "/api/source_notifications",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return SourceNotificationPostResponse.model_validate(unwrap(response))
