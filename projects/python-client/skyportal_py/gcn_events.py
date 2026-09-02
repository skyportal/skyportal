"""Typed endpoint functions for ``/api/gcn_event``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models._cyclic import (
    GcnEventCrossmatchStateResponse,
    GcnEventLocalizationResponse,
    GcnEventResponse,
    GcnEventUserResponse,
    GcnNoticeResponse,
    GcnPropertyResponse,
    GcnReportResponse,
    GcnSummaryResponse,
    GcnTriggerResponse,
)
from skyportal_py_models.gcn_events import (
    DefaultGcnTagPost,
    DefaultGcnTagResponse,
    GcnCatalogQueryResponse,
    GcnEventCrossmatchRequeueResponse,
    GcnEventIdResponse,
    GcnEventInstrumentFieldsResponse,
    GcnEventObjCrossmatchPost,
    GcnEventObjIdResponse,
    GcnEventObjPost,
    GcnEventObjResponse,
    GcnEventPost,
    GcnEventPostResponse,
    GcnEventsPageResponse,
    GcnEventTachInfoResponse,
    GcnEventTagPostResponse,
    GcnReportPost,
    GcnSummaryPost,
)

from skyportal_py._http import unwrap, unwrap_content
from skyportal_py.observation_plans import ObservationPlanRequestResponse
from skyportal_py.survey_efficiency import SurveyEfficiencyForObservationsResponse

__all__ = [
    "DefaultGcnTagPost",
    "DefaultGcnTagResponse",
    "GcnCatalogQueryResponse",
    "GcnEventCrossmatchRequeueResponse",
    "GcnEventCrossmatchStateResponse",
    "GcnEventIdResponse",
    "GcnEventInstrumentFieldsResponse",
    "GcnEventLocalizationResponse",
    "GcnEventObjCrossmatchPost",
    "GcnEventObjIdResponse",
    "GcnEventObjPost",
    "GcnEventObjResponse",
    "GcnEventPost",
    "GcnEventPostResponse",
    "GcnEventResponse",
    "GcnEventTachInfoResponse",
    "GcnEventTagPostResponse",
    "GcnEventUserResponse",
    "GcnEventsPageResponse",
    "GcnNoticeResponse",
    "GcnPropertyResponse",
    "GcnReportPost",
    "GcnReportResponse",
    "GcnSummaryPost",
    "GcnSummaryResponse",
    "GcnTriggerResponse",
]


def post_gcn_event(
    client: httpx.Client,
    payload: GcnEventPost,
) -> GcnEventPostResponse:
    """Ingest a GCN event from a VOEvent, a JSON notice or a dictionary.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : GcnEventPost
        The event to ingest. Provide ``xml`` (a VOEvent) or ``json_notice``
        (a GCN JSON notice); otherwise ``dateobs`` is required and the
        remaining fields describe the event. ``skymap`` accepts a
        multi-order map, a base64 FITS blob, a URL, or a cone/ellipse/polygon
        description. ``notice_id`` in the response is null for the
        dictionary form.
    """
    response = client.post(
        "/api/gcn_event",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return GcnEventPostResponse.model_validate(unwrap(response))


def fetch_gcn_event(
    client: httpx.Client,
    dateobs: str,
    *,
    exclude_notice_content: bool = False,
) -> GcnEventResponse:
    """Retrieve a single GCN event, with its localizations and summaries.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp, e.g. ``"2023-05-23T12:00:00"``.
    exclude_notice_content : bool, optional
        Omit the raw notice content from each entry of ``gcn_notices``.
        Defaults to false server-side.
    """
    response = client.get(
        f"/api/gcn_event/{dateobs}",
        params={"excludeNoticeContent": exclude_notice_content},
    )
    return GcnEventResponse.model_validate(unwrap(response))


def fetch_gcn_events(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    partial_dateobs: str | None = None,
    gcn_tag_keep: list[str] | None = None,
    gcn_tag_remove: list[str] | None = None,
    localization_tag_keep: list[str] | None = None,
    localization_tag_remove: list[str] | None = None,
    gcn_properties_filter: list[str] | None = None,
    localization_properties_filter: list[str] | None = None,
    group_ids: list[int] | None = None,
    mmadetector_ids: list[int] | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
) -> GcnEventsPageResponse:
    """Query GCN events, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls. The server caps the page size.
    start_date, end_date : str, optional
        Arrow-parseable bounds on ``dateobs``.
    partial_dateobs : str, optional
        Prefix of a ``dateobs`` (or a substring of an alias) to match.
        Cannot be combined with :func:`fetch_gcn_event`'s path lookup.
    gcn_tag_keep, gcn_tag_remove : list of str, optional
        Keep events carrying any of these GCN tags, or drop them.
    localization_tag_keep, localization_tag_remove : list of str, optional
        The same, applied to the tags of the events' localizations.
    gcn_properties_filter : list of str, optional
        Property filters, each ``"name"`` or ``"name: value: operator"``
        (operator in ``lt``, ``le``, ``eq``, ``ne``, ``ge``, ``gt``).
    localization_properties_filter : list of str, optional
        The same, applied to localization properties.
    group_ids : list of int, optional
        Return only events shared with at least one of these groups. This
        narrows what the token can already read, it does not widen it.
    mmadetector_ids : list of int, optional
        Return only events any of these MMA detectors contributed to.
    sort_by : str, optional
        Only ``"dateobs"`` is supported. Defaults to newest first.
    sort_order : str, optional
        ``"asc"`` or ``"desc"``.
    """
    params: dict[str, str | int] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "sortOrder": sort_order,
    }
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    if partial_dateobs is not None:
        params["partialdateobs"] = partial_dateobs
    if gcn_tag_keep is not None:
        params["gcnTagKeep"] = ",".join(gcn_tag_keep)
    if gcn_tag_remove is not None:
        params["gcnTagRemove"] = ",".join(gcn_tag_remove)
    if localization_tag_keep is not None:
        params["localizationTagKeep"] = ",".join(localization_tag_keep)
    if localization_tag_remove is not None:
        params["localizationTagRemove"] = ",".join(localization_tag_remove)
    if gcn_properties_filter is not None:
        params["gcnPropertiesFilter"] = ",".join(gcn_properties_filter)
    if localization_properties_filter is not None:
        params["localizationPropertiesFilter"] = ",".join(
            localization_properties_filter
        )
    if group_ids is not None:
        params["groupIds"] = ",".join(str(gid) for gid in group_ids)
    if mmadetector_ids is not None:
        params["mmadetectorIds"] = ",".join(str(mid) for mid in mmadetector_ids)
    if sort_by is not None:
        params["sortBy"] = sort_by
    response = client.get("/api/gcn_event", params=params)
    return GcnEventsPageResponse.model_validate(unwrap(response))


def delete_gcn_event(client: httpx.Client, dateobs: str) -> None:
    """Delete a GCN event, along with its localizations, notices and tags.

    Requires the ``System admin`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event to delete.
    """
    unwrap(client.delete(f"/api/gcn_event/{dateobs}"))


def post_gcn_event_alias(client: httpx.Client, dateobs: str, alias: str) -> None:
    """Add an alias to a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    alias : str
        Alias to add. The server rejects an alias the event already has.
    """
    unwrap(client.post(f"/api/gcn_event/{dateobs}/alias", json={"alias": alias}))


def delete_gcn_event_alias(client: httpx.Client, dateobs: str, alias: str) -> None:
    """Remove an alias from a GCN event.

    Aliases containing ``LVC#`` or ``FERMI#`` cannot be removed.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    alias : str
        Alias to remove.
    """
    unwrap(
        client.request(
            "DELETE",
            f"/api/gcn_event/{dateobs}/alias",
            json={"alias": alias},
        )
    )


def fetch_gcn_event_tags(
    client: httpx.Client,
    *,
    detector_type: str | None = None,
) -> list[str]:
    """Retrieve all distinct GCN event tags.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    detector_type : str, optional
        Keep only the tags of events an MMA detector of this type
        contributed to.
    """
    params = {} if detector_type is None else {"detectorType": detector_type}
    response = client.get("/api/gcn_event/tags", params=params)
    return [str(tag) for tag in unwrap(response)]


def post_gcn_event_tag(
    client: httpx.Client,
    dateobs: str,
    text: str,
) -> GcnEventTagPostResponse:
    """Tag a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event to tag.
    text : str
        The tag text.
    """
    response = client.post(
        "/api/gcn_event/tags",
        json={"dateobs": dateobs, "text": text},
    )
    return GcnEventTagPostResponse.model_validate(unwrap(response))


def delete_gcn_event_tag(client: httpx.Client, dateobs: str, tag: str) -> None:
    """Remove a tag from a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the tagged event.
    tag : str
        Text of the tag to remove.
    """
    unwrap(
        client.request(
            "DELETE",
            f"/api/gcn_event/tags/{dateobs}",
            json={"tag": tag},
        )
    )


def fetch_gcn_event_properties(client: httpx.Client) -> list[str]:
    """Retrieve all distinct GCN event property names, sorted.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/gcn_event/properties")
    return [str(name) for name in unwrap(response)]


def fetch_gcn_event_survey_efficiency(
    client: httpx.Client,
    gcnevent_id: int,
) -> list[SurveyEfficiencyForObservationsResponse]:
    """Retrieve the survey efficiency analyses of a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    gcnevent_id : int
        Numeric ID of the GCN event (not its ``dateobs``).
    """
    response = client.get(f"/api/gcn_event/{gcnevent_id}/survey_efficiency")
    return [
        SurveyEfficiencyForObservationsResponse.model_validate(analysis)
        for analysis in unwrap(response)
    ]


def fetch_gcn_event_observation_plan_requests(
    client: httpx.Client,
    gcnevent_id: int,
) -> list[ObservationPlanRequestResponse]:
    """Retrieve the observation plan requests of a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    gcnevent_id : int
        Numeric ID of the GCN event (not its ``dateobs``).
    """
    response = client.get(f"/api/gcn_event/{gcnevent_id}/observation_plan_requests")
    return [
        ObservationPlanRequestResponse.model_validate(request)
        for request in unwrap(response)
    ]


def fetch_gcn_event_catalog_queries(
    client: httpx.Client,
    gcnevent_id: int,
) -> list[GcnCatalogQueryResponse]:
    """Retrieve the catalog queries submitted for a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    gcnevent_id : int
        Numeric ID of the GCN event (not its ``dateobs``).
    """
    response = client.get(f"/api/gcn_event/{gcnevent_id}/catalog_query")
    return [GcnCatalogQueryResponse.model_validate(query) for query in unwrap(response)]


def post_gcn_event_user(client: httpx.Client, dateobs: str, user_id: int) -> None:
    """Add a user as an advocate for a GCN event.

    The user is notified in SkyPortal.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    user_id : int
        ID of the user to add.
    """
    unwrap(client.post(f"/api/gcn_event/{dateobs}/users", json={"userID": user_id}))


def delete_gcn_event_user(client: httpx.Client, dateobs: str, user_id: int) -> None:
    """Remove a user from the advocates of a GCN event.

    Only the user themselves (or a system admin) may be removed.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    user_id : int
        ID of the user to remove.
    """
    unwrap(client.delete(f"/api/gcn_event/{dateobs}/users/{user_id}"))


def fetch_gcn_event_notice_download(
    client: httpx.Client,
    dateobs: str,
    notice_id: int,
) -> bytes:
    """Download the raw content of a GCN notice.

    The payload is XML for VOEvent notices, JSON for JSON notices, and plain
    text otherwise.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event the notice belongs to.
    notice_id : int
        ID of the notice to download.
    """
    response = client.get(
        f"/api/gcn_event/{dateobs}/notice/{notice_id}/download",
    )
    return unwrap_content(response)


def post_gcn_event_gracedb(client: httpx.Client, dateobs: str) -> GcnEventIdResponse:
    """Scrape GraceDB for a gravitational-wave event's logs and labels.

    The scrape runs in the background; the event must already carry an
    ``LVC#`` alias. Requires the ``Manage GCNs`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    """
    response = client.post(f"/api/gcn_event/{dateobs}/gracedb")
    return GcnEventIdResponse.model_validate(unwrap(response))


def post_gcn_event_tach(client: httpx.Client, dateobs: str) -> GcnEventIdResponse:
    """Scrape TACH for a GCN event's aliases and circulars.

    The scrape runs in the background. Requires the ``Manage GCNs``
    permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    """
    response = client.post(f"/api/gcn_event/{dateobs}/tach")
    return GcnEventIdResponse.model_validate(unwrap(response))


def fetch_gcn_event_tach(
    client: httpx.Client, dateobs: str
) -> GcnEventTachInfoResponse:
    """Retrieve the TACH ID, aliases and circulars of a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    """
    response = client.get(f"/api/gcn_event/{dateobs}/tach")
    return GcnEventTachInfoResponse.model_validate(unwrap(response))


def fetch_gcn_event_crossmatch(
    client: httpx.Client,
    dateobs: str,
) -> list[GcnEventCrossmatchStateResponse]:
    """Retrieve the per-filter alert crossmatch progress of a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    """
    response = client.get(f"/api/gcn_event/{dateobs}/crossmatch")
    return [
        GcnEventCrossmatchStateResponse.model_validate(state)
        for state in unwrap(response)
    ]


def post_gcn_event_crossmatch(
    client: httpx.Client,
    dateobs: str,
) -> GcnEventCrossmatchRequeueResponse:
    """Requeue the alert crossmatch of a GCN event.

    Every filter is re-queried from the start of the window, including the
    one-shot archival pass. Existing sources and annotations are refreshed in
    place rather than duplicated. Requires the ``Manage GCNs`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    """
    response = client.post(f"/api/gcn_event/{dateobs}/crossmatch")
    return GcnEventCrossmatchRequeueResponse.model_validate(unwrap(response))


def fetch_gcn_event_instrument_fields(
    client: httpx.Client,
    dateobs: str,
    instrument_id: int,
    *,
    localization_name: str | None = None,
    integrated_probability: float = 0.95,
) -> GcnEventInstrumentFieldsResponse:
    """Compute an instrument's field probabilities for an event localization.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    instrument_id : int
        ID of the instrument whose fields are tiled against the skymap.
    localization_name : str, optional
        Name of the localization to use. Defaults to one of the event's
        localizations chosen by the server.
    integrated_probability : float, optional
        Cumulative probability threshold, defaults to 0.95.
    """
    params: dict[str, str | float] = {"integrated_probability": integrated_probability}
    if localization_name is not None:
        params["localization_name"] = localization_name
    response = client.get(
        f"/api/gcn_event/{dateobs}/instrument/{instrument_id}",
        params=params,
    )
    return GcnEventInstrumentFieldsResponse.model_validate(unwrap(response))


def fetch_gcn_event_triggers(
    client: httpx.Client,
    dateobs: str,
    *,
    allocation_id: int | None = None,
) -> list[GcnTriggerResponse]:
    """Retrieve the triggered status of a GCN event, per allocation.

    Requires the ``Manage allocations`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    allocation_id : int, optional
        Restrict to a single allocation.
    """
    path = f"/api/gcn_event/{dateobs}/triggered"
    if allocation_id is not None:
        path = f"{path}/{allocation_id}"
    response = client.get(path)
    return [GcnTriggerResponse.model_validate(trigger) for trigger in unwrap(response)]


def update_gcn_event_trigger(
    client: httpx.Client,
    dateobs: str,
    allocation_id: int,
    *,
    triggered: bool,
) -> GcnTriggerResponse:
    """Set whether a GCN event triggered an allocation.

    The record is created if it does not exist. Requires the
    ``Manage allocations`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    allocation_id : int
        ID of the allocation.
    triggered : bool
        The new triggered status.
    """
    response = client.put(
        f"/api/gcn_event/{dateobs}/triggered/{allocation_id}",
        json={"triggered": triggered},
    )
    return GcnTriggerResponse.model_validate(unwrap(response))


def delete_gcn_event_trigger(
    client: httpx.Client,
    dateobs: str,
    allocation_id: int,
) -> GcnTriggerResponse:
    """Delete the triggered status of a GCN event for an allocation.

    Returns the deleted record. Requires the ``Manage allocations``
    permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    allocation_id : int
        ID of the allocation.
    """
    response = client.delete(f"/api/gcn_event/{dateobs}/triggered/{allocation_id}")
    return GcnTriggerResponse.model_validate(unwrap(response))


def post_gcn_summary(
    client: httpx.Client,
    dateobs: str,
    payload: GcnSummaryPost,
) -> GcnEventIdResponse:
    """Generate a summary of a GCN event.

    The summary is written in the background: the record is created
    immediately with the text ``"pending"`` and filled in later. Unless
    ``no_text`` is set, ``subject`` is required. A user may not have two
    summaries with the same title for the same event and group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    payload : GcnSummaryPost
        What to include in the summary. ``localization_cumprob`` defaults to
        0.95, ``number_detections`` to 2, ``number_observations`` to 1 and
        ``stats_method`` to ``"python"`` (``"db"`` is the alternative).
    """
    response = client.post(
        f"/api/gcn_event/{dateobs}/summary",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return GcnEventIdResponse.model_validate(unwrap(response))


def fetch_gcn_summary(
    client: httpx.Client,
    dateobs: str,
    summary_id: int,
) -> GcnSummaryResponse:
    """Retrieve a GCN event summary, including its text.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the summarized event.
    summary_id : int
        ID of the summary.
    """
    response = client.get(f"/api/gcn_event/{dateobs}/summary/{summary_id}")
    return GcnSummaryResponse.model_validate(unwrap(response))


def update_gcn_summary(
    client: httpx.Client,
    dateobs: str,
    summary_id: int,
    body: str,
) -> GcnSummaryResponse:
    """Replace the text of a GCN event summary.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the summarized event.
    summary_id : int
        ID of the summary to update.
    body : str
        The new summary text.
    """
    response = client.patch(
        f"/api/gcn_event/{dateobs}/summary/{summary_id}",
        json={"body": body},
    )
    return GcnSummaryResponse.model_validate(unwrap(response))


def delete_gcn_summary(
    client: httpx.Client,
    dateobs: str,
    summary_id: int,
) -> None:
    """Delete a GCN event summary.

    A summary that is still pending cannot be deleted within an hour of
    being created.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the summarized event.
    summary_id : int
        ID of the summary to delete.
    """
    unwrap(client.delete(f"/api/gcn_event/{dateobs}/summary/{summary_id}"))


def post_gcn_report(
    client: httpx.Client,
    dateobs: str,
    payload: GcnReportPost,
) -> GcnEventIdResponse:
    """Generate a report on a GCN event.

    The report is assembled in the background: the record is created
    immediately with pending data and filled in later. A user may not have
    two reports with the same name for the same event and group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    payload : GcnReportPost
        What to include in the report. ``localization_cumprob`` defaults to
        0.95, ``number_detections`` to 2 and ``stats_method`` to
        ``"python"`` (``"db"`` is the alternative).
    """
    response = client.post(
        f"/api/gcn_event/{dateobs}/report",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return GcnEventIdResponse.model_validate(unwrap(response))


def fetch_gcn_reports(client: httpx.Client, dateobs: str) -> list[GcnReportResponse]:
    """Retrieve the reports of a GCN event, newest first.

    The report data itself is omitted; use :func:`fetch_gcn_report` for it.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    """
    response = client.get(f"/api/gcn_event/{dateobs}/report")
    return [GcnReportResponse.model_validate(report) for report in unwrap(response)]


def fetch_gcn_report(
    client: httpx.Client,
    dateobs: str,
    report_id: int,
) -> GcnReportResponse:
    """Retrieve a single GCN event report, including its data.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    report_id : int
        ID of the report.
    """
    response = client.get(f"/api/gcn_event/{dateobs}/report/{report_id}")
    return GcnReportResponse.model_validate(unwrap(response))


def update_gcn_report(
    client: httpx.Client,
    dateobs: str,
    report_id: int,
    *,
    data: dict[str, Any] | None = None,
    published: bool | None = None,
) -> GcnReportResponse:
    """Update a GCN event report, or publish and unpublish it.

    Sources added to ``data`` are re-fetched from the database with their
    photometry; duplicates are rejected. When ``published`` is omitted the
    server regenerates the rendered report instead.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    report_id : int
        ID of the report to update.
    data : dict, optional
        The new report data.
    published : bool, optional
        Publish (true) or unpublish (false) the report.
    """
    payload: dict[str, Any] = {}
    if data is not None:
        payload["data"] = data
    if published is not None:
        payload["published"] = published
    response = client.patch(
        f"/api/gcn_event/{dateobs}/report/{report_id}",
        json=payload,
    )
    return GcnReportResponse.model_validate(unwrap(response))


def delete_gcn_report(
    client: httpx.Client,
    dateobs: str,
    report_id: int,
) -> None:
    """Delete a GCN event report, unpublishing it first.

    A report that is still pending cannot be deleted within an hour of being
    created.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    report_id : int
        ID of the report to delete.
    """
    unwrap(client.delete(f"/api/gcn_event/{dateobs}/report/{report_id}"))


def post_default_gcn_tag(
    client: httpx.Client,
    payload: DefaultGcnTagPost,
) -> GcnEventIdResponse:
    """Create a rule that automatically tags matching GCN events.

    Requires the ``Manage GCNs`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : DefaultGcnTagPost
        The rule to create. ``default_tag_name`` must be unique. ``filters``
        accepts the keys ``gcn_tags``, ``notice_types`` and
        ``localization_tags``, each a list of strings.
    """
    response = client.post(
        "/api/default_gcn_tag",
        json=payload.model_dump(exclude_none=True),
    )
    return GcnEventIdResponse.model_validate(unwrap(response))


def fetch_default_gcn_tag(
    client: httpx.Client,
    default_gcn_tag_id: int,
) -> DefaultGcnTagResponse:
    """Retrieve a single default GCN tag.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    default_gcn_tag_id : int
        ID of the default GCN tag.
    """
    response = client.get(f"/api/default_gcn_tag/{default_gcn_tag_id}")
    return DefaultGcnTagResponse.model_validate(unwrap(response))


def fetch_default_gcn_tags(client: httpx.Client) -> list[DefaultGcnTagResponse]:
    """Retrieve all default GCN tags.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/default_gcn_tag")
    return [DefaultGcnTagResponse.model_validate(tag) for tag in unwrap(response)]


def delete_default_gcn_tag(
    client: httpx.Client,
    default_gcn_tag_id: int,
) -> None:
    """Delete a default GCN tag.

    Requires the ``Manage GCNs`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    default_gcn_tag_id : int
        ID of the default GCN tag to delete.
    """
    unwrap(client.delete(f"/api/default_gcn_tag/{default_gcn_tag_id}"))


def fetch_gcn_event_sources(
    client: httpx.Client,
    dateobs: str,
    *,
    source_ids: list[str] | None = None,
) -> list[GcnEventObjResponse]:
    """Retrieve the objects vetted against a GCN event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    source_ids : list of str, optional
        Restrict to these object IDs. Defaults to every vetted object.
    """
    params: dict[str, str] = {}
    if source_ids is not None:
        params["sourcesIDList"] = ",".join(source_ids)
    response = client.get(f"/api/sources_in_gcn/{dateobs}", params=params)
    return [GcnEventObjResponse.model_validate(source) for source in unwrap(response)]


def fetch_gcn_event_source(
    client: httpx.Client,
    dateobs: str,
    obj_id: str,
) -> list[GcnEventObjResponse]:
    """Retrieve one object's standing against a GCN event.

    The server returns a list, empty when the object has not been vetted
    against the event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    obj_id : str
        Object ID, e.g. ``"ZTF20abcdef"``.
    """
    response = client.get(f"/api/sources_in_gcn/{dateobs}/{obj_id}")
    return [GcnEventObjResponse.model_validate(source) for source in unwrap(response)]


def post_gcn_event_source(
    client: httpx.Client,
    dateobs: str,
    payload: GcnEventObjPost,
) -> GcnEventObjIdResponse:
    """Record an object's standing against a GCN event.

    An existing record for the object is updated instead. The server rejects
    a repost that changes neither status, explanation nor notes. Requires
    the ``Upload data`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    payload : GcnEventObjPost
        The object and its standing. ``status`` is one of ``"pending"``,
        ``"confirmed"``, ``"ambiguous"`` or ``"rejected"``.
    """
    response = client.post(
        f"/api/sources_in_gcn/{dateobs}",
        json=payload.model_dump(exclude_none=True),
    )
    return GcnEventObjIdResponse.model_validate(unwrap(response))


def update_gcn_event_source(  # noqa: PLR0913 -- mirrors the endpoint's request body
    client: httpx.Client,
    dateobs: str,
    obj_id: str,
    status: str,
    *,
    explanation: str | None = None,
    notes: str | None = None,
) -> GcnEventObjIdResponse:
    """Update an object's standing against a GCN event.

    Requires the ``Upload data`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    obj_id : str
        Object ID of the vetted object.
    status : str
        One of ``"pending"``, ``"confirmed"``, ``"ambiguous"`` or
        ``"rejected"``.
    explanation : str, optional
        Why the object was confirmed or rejected.
    notes : str, optional
        Extra information about the object.
    """
    payload: dict[str, str] = {"status": status}
    if explanation is not None:
        payload["explanation"] = explanation
    if notes is not None:
        payload["notes"] = notes
    response = client.patch(
        f"/api/sources_in_gcn/{dateobs}/{obj_id}",
        json=payload,
    )
    return GcnEventObjIdResponse.model_validate(unwrap(response))


def delete_gcn_event_source(
    client: httpx.Client,
    dateobs: str,
    obj_id: str,
) -> GcnEventObjIdResponse:
    """Remove an object's standing against a GCN event.

    The object's relation to the event becomes undefined again. Returns the
    ID of the deleted record. Requires the ``Upload data`` permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the event.
    obj_id : str
        Object ID of the vetted object.
    """
    response = client.delete(f"/api/sources_in_gcn/{dateobs}/{obj_id}")
    return GcnEventObjIdResponse.model_validate(unwrap(response))


def fetch_gcn_events_associated_with_source(
    client: httpx.Client,
    obj_id: str,
) -> list[str]:
    """Retrieve the ``dateobs`` of the GCN events an object is confirmed in.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID, e.g. ``"ZTF20abcdef"``.
    """
    response = client.get(f"/api/associated_gcns/{obj_id}")
    return [str(dateobs) for dateobs in unwrap(response)["gcns"]]


def post_gcn_event_obj_crossmatch(
    client: httpx.Client,
    obj_id: str,
    payload: GcnEventObjCrossmatchPost,
) -> None:
    """Crossmatch an object against the GCN events of a time window.

    The crossmatch runs in the background and records each containment as a
    pending object-in-event association, leaving decisions already made
    alone. The window may span at most 31 days.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID to crossmatch, e.g. ``"ZTF20abcdef"``.
    payload : GcnEventObjCrossmatchPost
        The window and filters. ``probability`` is the integrated
        probability contour to search within, defaulting to 0.95.
    """
    unwrap(
        client.post(
            f"/api/sources/{obj_id}/gcn_event",
            json=payload.model_dump(by_alias=True, exclude_none=True),
        )
    )
