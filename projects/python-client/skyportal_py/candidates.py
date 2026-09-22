"""Typed endpoint functions for ``/api/candidates``."""

from __future__ import annotations

import httpx
from skyportal_py_models.candidates import (
    BulkCandidateDeleteResponse,
    CandidateAssociatedObjResponse,
    CandidateFilterPageResponse,
    CandidatePassingAlertResponse,
    CandidatePost,
    CandidatePostResponse,
    CandidateRecordResponse,
    CandidateResponse,
    CandidatesPageResponse,
    ScanReportItemResponse,
    ScanReportPassedFiltersRange,
    ScanReportPost,
    ScanReportResponse,
    ScanReportSavedCandidatesRange,
    ScanReportsPageResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "BulkCandidateDeleteResponse",
    "CandidateAssociatedObjResponse",
    "CandidateFilterPageResponse",
    "CandidatePassingAlertResponse",
    "CandidatePost",
    "CandidatePostResponse",
    "CandidateRecordResponse",
    "CandidateResponse",
    "CandidatesPageResponse",
    "ScanReportItemResponse",
    "ScanReportPassedFiltersRange",
    "ScanReportPost",
    "ScanReportResponse",
    "ScanReportSavedCandidatesRange",
    "ScanReportsPageResponse",
]


def fetch_candidate(
    client: httpx.Client,
    obj_id: str,
    *,
    include_photometry: bool = False,
    include_spectra: bool = False,
    include_alerts: bool = False,
) -> CandidateResponse:
    """Retrieve a single candidate by object ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the candidate, e.g. ``"ZTF20abcdef"``.
    include_photometry : bool, optional
        Include the candidate's photometry in ``photometry``.
    include_spectra : bool, optional
        Include the candidate's spectra in ``spectra``.
    include_alerts : bool, optional
        Include the filters the candidate passed and the alerts behind
        them, in ``filter_ids`` and ``passing_alerts``.
    """
    response = client.get(
        f"/api/candidates/{obj_id}",
        params={
            "includePhotometry": include_photometry,
            "includeSpectra": include_spectra,
            "includeAlerts": include_alerts,
        },
    )
    return CandidateResponse.model_validate(unwrap(response))


def candidate_exists(client: httpx.Client, obj_id: str) -> bool:
    """Check whether a candidate with this object ID exists.

    Uses the endpoint's HEAD form, which carries no body.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID to check.
    """
    return client.head(f"/api/candidates/{obj_id}").is_success


def fetch_candidates(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 25,
    group_ids: list[int] | None = None,
    filter_ids: list[int] | None = None,
    saved_status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    obj_id: str | None = None,
    name_only: bool | None = None,
    include_photometry: bool = False,
    sort_by_annotation_origin: str | None = None,
    sort_by_annotation_key: str | None = None,
    sort_by_annotation_order: str | None = None,
    annotation_filter_list: str | None = None,
    classifications: list[str] | None = None,
    classifications_reject: list[str] | None = None,
    min_redshift: float | None = None,
    max_redshift: float | None = None,
    list_name: str | None = None,
    list_name_reject: str | None = None,
    query_id: str | None = None,
    photometry_annotations_filter: str | None = None,
    photometry_annotations_filter_origin: str | None = None,
    photometry_annotations_filter_before: str | None = None,
    photometry_annotations_filter_after: str | None = None,
    photometry_annotations_filter_min_count: int | None = None,
    first_detection_after: str | None = None,
    last_detection_before: str | None = None,
    number_detections: int | None = None,
    require_detections: bool = True,
    exclude_forced_photometry: bool = False,
    localization_dateobs: str | None = None,
    localization_name: str | None = None,
    localization_cumprob: float | None = None,
    autosave: bool = False,
    autosave_group_ids: list[int] | None = None,
) -> CandidatesPageResponse:
    """Query candidates, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls.
    group_ids : list of int, optional
        Restrict to candidates passing filters belonging to these groups.
    filter_ids : list of int, optional
        Restrict to candidates passing these filters. Defaults to every
        filter of the token's groups when ``group_ids`` is not given.
    saved_status : str, optional
        FilterResponse on whether candidates are saved as sources, e.g. ``"all"``
        or ``"savedToAllSelected"``.
    start_date, end_date : str, optional
        Restrict to candidates that passed a filter in this ISO-format
        (UTC) time range.
    obj_id : str, optional
        Partial object ID to autocomplete against.
    name_only : bool, optional
        With ``obj_id``, return only the matching object IDs.
    include_photometry : bool, optional
        Include each candidate's photometry in ``photometry``.
    sort_by_annotation_origin, sort_by_annotation_key : str, optional
        Sort the page by this annotation key from this origin; provide
        both together.
    sort_by_annotation_order : str, optional
        Direction of the annotation sort, ``"asc"`` (the server default)
        or ``"desc"``.
    annotation_filter_list : str, optional
        JSON-encoded list of ``{"origin", "key", "min"/"max"/"value"}``
        annotation constraints, as the frontend scanner sends it.
    classifications : list of str, optional
        Keep candidates carrying one of these classifications.
    classifications_reject : list of str, optional
        Drop candidates carrying any of these classifications.
    min_redshift, max_redshift : float, optional
        Redshift range filter.
    list_name : str, optional
        Keep only candidates saved to this list of the querying user,
        e.g. ``"favorites"``.
    list_name_reject : str, optional
        Drop candidates saved to this list of the querying user, e.g.
        ``"rejected_candidates"``.
    query_id : str, optional
        Replay a previously cached query; the response's ``query_id``
        identifies the cache entry.
    photometry_annotations_filter : str, optional
        Comma-separated ``key[:value:operator]`` constraints on photometry
        annotations.
    photometry_annotations_filter_origin : str, optional
        Comma-separated origins the photometry annotations must come from.
    photometry_annotations_filter_before, photometry_annotations_filter_after : str, optional
        ISO-format bounds on the photometry annotations' creation time.
    photometry_annotations_filter_min_count : int, optional
        Require at least this many photometry annotations passing the
        photometry-annotation filters. Server default is 1.
    first_detection_after, last_detection_before : str, optional
        ISO-format (UTC) bounds on when the candidates were first/last
        detected.
    number_detections : int, optional
        Keep only candidates detected at least this many times.
    require_detections : bool, optional
        Only apply the detection filters above, and require them to be set
        when querying within a localization. Server default is true.
    exclude_forced_photometry : bool, optional
        Ignore forced photometry when applying the detection filters.
    localization_dateobs : str, optional
        Restrict to candidates inside a GCN localization, identified by
        its event time in ISO format.
    localization_name : str, optional
        Name of the localization/skymap to use; defaults to the event's
        most recent localization.
    localization_cumprob : float, optional
        Cumulative probability of the localization up to which to include
        candidates. Server default is 0.95.
    autosave : bool, optional
        Save every candidate the query returns as a source.
    autosave_group_ids : list of int, optional
        Groups to save autosaved candidates to; defaults to all of the
        token's groups.
    """
    optional = {
        "groupIDs": None
        if group_ids is None
        else ",".join(str(gid) for gid in group_ids),
        "filterIDs": None
        if filter_ids is None
        else ",".join(str(fid) for fid in filter_ids),
        "savedStatus": saved_status,
        "startDate": start_date,
        "endDate": end_date,
        "objID": obj_id,
        "nameOnly": name_only,
        "sortByAnnotationOrigin": sort_by_annotation_origin,
        "sortByAnnotationKey": sort_by_annotation_key,
        "sortByAnnotationOrder": sort_by_annotation_order,
        "annotationFilterList": annotation_filter_list,
        "classifications": None
        if classifications is None
        else ",".join(classifications),
        "classificationsReject": None
        if classifications_reject is None
        else ",".join(classifications_reject),
        "minRedshift": min_redshift,
        "maxRedshift": max_redshift,
        "listName": list_name,
        "listNameReject": list_name_reject,
        "queryID": query_id,
        "photometryAnnotationsFilter": photometry_annotations_filter,
        "photometryAnnotationsFilterOrigin": photometry_annotations_filter_origin,
        "photometryAnnotationsFilterBefore": photometry_annotations_filter_before,
        "photometryAnnotationsFilterAfter": photometry_annotations_filter_after,
        "photometryAnnotationsFilterMinCount": photometry_annotations_filter_min_count,
        "firstDetectionAfter": first_detection_after,
        "lastDetectionBefore": last_detection_before,
        "numberDetections": number_detections,
        "localizationDateobs": localization_dateobs,
        "localizationName": localization_name,
        "localizationCumprob": localization_cumprob,
        "autosaveGroupIds": None
        if autosave_group_ids is None
        else ",".join(str(gid) for gid in autosave_group_ids),
    }
    params: dict[str, str | int | float | bool] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "includePhotometry": include_photometry,
        "requireDetections": require_detections,
        "excludeForcedPhotometry": exclude_forced_photometry,
        "autosave": autosave,
        **{key: value for key, value in optional.items() if value is not None},
    }
    response = client.get("/api/candidates", params=params)
    return CandidatesPageResponse.model_validate(unwrap(response))


def post_candidate(
    client: httpx.Client,
    payload: CandidatePost,
) -> CandidatePostResponse:
    """Post a new candidate.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : CandidatePost
        The candidate to post, including the filters it passed
        (``filter_ids``) and when it passed them (``passed_at``).
    """
    response = client.post(
        "/api/candidates", json=payload.model_dump(exclude_none=True)
    )
    return CandidatePostResponse.model_validate(unwrap(response))


def delete_candidate(client: httpx.Client, obj_id: str, filter_id: int) -> None:
    """Delete the candidate entries for an object on a given filter.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the candidate, e.g. ``"ZTF20abcdef"``.
    filter_id : int
        ID of the filter the candidate passed. The server errors if no
        candidate matches this ``(obj_id, filter_id)`` pairing.
    """
    unwrap(client.delete(f"/api/candidates/{obj_id}/{filter_id}"))


def bulk_delete_candidates(
    client: httpx.Client,
    *,
    max_age_months: int | None = None,
    batch_size: int | None = None,
    dry_run: bool | None = None,
) -> BulkCandidateDeleteResponse:
    """Bulk-delete old, unsaved candidate objects.

    Deletes objects that appear as candidates, are not saved as an active
    source in any group, and whose most recent ``passed_at`` is older than
    ``max_age_months``. Deleting an object cascades to its candidates,
    photometry, annotations and thumbnails. Requires the ``System admin``
    permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    max_age_months : int, optional
        Age threshold in months. Server default is 6.
    batch_size : int, optional
        Maximum number of objects deleted in this call, oldest first.
        Server default is 1000; must be between 1 and 10000.
    dry_run : bool, optional
        If true, only report how many objects would be deleted. Server
        default is false.
    """
    payload: dict[str, int | bool] = {}
    if max_age_months is not None:
        payload["maxAgeMonths"] = max_age_months
    if batch_size is not None:
        payload["batchSize"] = batch_size
    if dry_run is not None:
        payload["dryRun"] = dry_run
    response = client.post("/api/candidates/bulk_delete", json=payload)
    return BulkCandidateDeleteResponse.model_validate(unwrap(response))


def fetch_candidates_filter(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 25,
    group_ids: list[int] | None = None,
    filter_ids: list[int] | None = None,
    saved_status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> CandidateFilterPageResponse:
    """Query the raw candidate rows, rather than the objects behind them.

    This is the lighter counterpart of :func:`fetch_candidates`: it returns
    ``candidates`` table rows, including ``passing_alert_id`` (the alert
    candid), which is what maps a candidate back to the upstream alert.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls. Rows are ordered by ``passed_at`` ascending.
        ``total_matches`` is only computed for page 1; keep it client-side
        while paginating.
    group_ids, filter_ids : list of int, optional
        Restrict to these groups and filters. Both default to everything
        accessible to the token.
    saved_status : str, optional
        FilterResponse on whether candidates are saved as sources, e.g. ``"all"``
        (the server default) or ``"savedToAllSelected"``.
    start_date, end_date : str, optional
        Restrict to candidates that passed a filter in this ISO-format
        (UTC) time range.
    """
    params: dict[str, str | int] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if group_ids is not None:
        params["groupIDs"] = ",".join(str(gid) for gid in group_ids)
    if filter_ids is not None:
        params["filterIDs"] = ",".join(str(fid) for fid in filter_ids)
    if saved_status is not None:
        params["savedStatus"] = saved_status
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    response = client.get("/api/candidates_filter", params=params)
    return CandidateFilterPageResponse.model_validate(unwrap(response))


def post_scan_report(client: httpx.Client, payload: ScanReportPost) -> None:
    """Generate a candidate scanning report.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ScanReportPost
        Groups owning the report plus the two time ranges it covers. Each
        range may instead be given as a rolling window in hours ending
        now (``passed_filters_window_hours``,
        ``saved_candidates_window_hours``); the explicit ranges win when
        both are supplied. The server errors if a report already exists
        for the same groups and options, or if no saved sources match.
    """
    unwrap(
        client.post(
            "/api/candidates/scan_reports",
            json=payload.model_dump(exclude_none=True),
        )
    )


def fetch_scan_reports(
    client: httpx.Client,
    *,
    page: int = 1,
    num_per_page: int = 10,
) -> ScanReportsPageResponse:
    """Retrieve candidate scanning reports, newest first.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page, num_per_page : int, optional
        Pagination controls.
    """
    params = {"page": page, "numPerPage": num_per_page}
    response = client.get("/api/candidates/scan_reports", params=params)
    return ScanReportsPageResponse.model_validate(unwrap(response))


def fetch_scan_report_items(
    client: httpx.Client,
    report_id: int,
) -> list[ScanReportItemResponse]:
    """Retrieve every item of a candidate scanning report.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    report_id : int
        ID of the scanning report.
    """
    response = client.get(f"/api/candidates/scan_reports/{report_id}/items")
    return [ScanReportItemResponse.model_validate(item) for item in unwrap(response)]


def update_scan_report_item(
    client: httpx.Client,
    report_id: int,
    item_id: int,
    *,
    comment: str | None = None,
) -> None:
    """Set the comment on one item of a candidate scanning report.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    report_id : int
        ID of the scanning report holding the item.
    item_id : int
        ID of the report item to update.
    comment : str, optional
        The comment to store. Passing ``None`` clears it, since the server
        overwrites the item's ``comment`` key with whatever is sent.
    """
    unwrap(
        client.patch(
            f"/api/candidates/scan_reports/{report_id}/items/{item_id}",
            json={"comment": comment},
        )
    )
