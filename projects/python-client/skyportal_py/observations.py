"""Typed endpoint functions for ``/api/observation``."""

from __future__ import annotations

import json
from typing import Any

import httpx
from skyportal_py_models.observations import (
    ObservationPost,
    ObservationQueuesResponse,
    ObservationResponse,
    ObservationSimSurveyResponse,
    ObservationsPageResponse,
)

from skyportal_py._http import unwrap, unwrap_content

__all__ = [
    "ObservationPost",
    "ObservationQueuesResponse",
    "ObservationResponse",
    "ObservationSimSurveyResponse",
    "ObservationsPageResponse",
]


def fetch_observations(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    start_date: str,
    end_date: str,
    telescope_name: str | None = None,
    instrument_name: str | None = None,
    localization_dateobs: str | None = None,
    localization_name: str | None = None,
    localization_cumprob: float | None = None,
    number_observations: int | None = None,
    return_statistics: bool = False,
    stats_method: str | None = None,
    stats_logging: bool = False,
    include_geojson: bool = False,
    observation_status: str | None = None,
    page_number: int = 1,
    num_per_page: int = 100,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> ObservationsPageResponse:
    """Query executed (or queued) survey observations, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    start_date, end_date : str
        Restrict to observations taken in this time range, as ISO-format
        date strings. Both are required by the server.
    telescope_name, instrument_name : str, optional
        Restrict to observations by this telescope/instrument.
    localization_dateobs : str, optional
        GCN event time in ISO 8601 format; restricts to observations
        overlapping the event's localization.
    localization_name : str, optional
        Name of the localization / skymap to use. Defaults to the event's
        most recent localization.
    localization_cumprob : float, optional
        Cumulative probability up to which to include fields.
        Server default 0.95.
    number_observations : int, optional
        Minimum number of observations of a field required to include it.
        Server default 1.
    return_statistics : bool, optional
        Include integrated probability and area (requires
        ``localization_dateobs``).
    stats_method : str, optional
        ``"python"`` (server default) or ``"db"``.
    stats_logging : bool, optional
        Log the stats computation time server-side.
    include_geojson : bool, optional
        Include associated GeoJSON contours and field IDs.
    observation_status : str, optional
        ``"executed"`` (server default) or ``"queued"``.
    page_number, num_per_page : int, optional
        Pagination controls; ``num_per_page`` can be at most 10000.
    sort_by : str, optional
        Field to sort by, e.g. ``"obstime"``.
    sort_order : str, optional
        ``"asc"`` or ``"desc"``. Defaults to ``"asc"``.
    """
    params: dict[str, str | int | float | bool] = {
        "startDate": start_date,
        "endDate": end_date,
        "returnStatistics": return_statistics,
        "statsLogging": stats_logging,
        "includeGeoJSON": include_geojson,
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if telescope_name is not None:
        params["telescopeName"] = telescope_name
    if instrument_name is not None:
        params["instrumentName"] = instrument_name
    if localization_dateobs is not None:
        params["localizationDateobs"] = localization_dateobs
    if localization_name is not None:
        params["localizationName"] = localization_name
    if localization_cumprob is not None:
        params["localizationCumprob"] = localization_cumprob
    if number_observations is not None:
        params["numberObservations"] = number_observations
    if stats_method is not None:
        params["statsMethod"] = stats_method
    if observation_status is not None:
        params["observationStatus"] = observation_status
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_order is not None:
        params["sortOrder"] = sort_order
    response = client.get("/api/observation", params=params)
    return ObservationsPageResponse.model_validate(unwrap(response))


def post_observation(client: httpx.Client, payload: ObservationPost) -> None:
    """Ingest a set of executed observations for an instrument.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ObservationPost
        The observations to ingest. ``observation_data`` maps column names
        to equal-length lists and must include ``observation_id``,
        ``field_id`` (or ``RA`` and ``Dec``), ``obstime``, ``filter``, and
        ``exposure_time``. Ingestion runs asynchronously server-side.
    """
    unwrap(
        client.post(
            "/api/observation",
            json=payload.model_dump(by_alias=True, exclude_none=True),
        )
    )


def delete_observation(client: httpx.Client, observation_id: int) -> None:
    """Delete an executed observation.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_id : int
        Database ID of the executed observation (not the
        instrument-supplied ``observation_id``).
    """
    unwrap(client.delete(f"/api/observation/{observation_id}"))


def post_observation_ascii(
    client: httpx.Client,
    instrument_id: int,
    observation_data: str,
) -> None:
    """Upload executed observations from an ASCII (CSV) table.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument the observations belong to.
    observation_data : str
        Comma-separated table with columns ``observation_id``,
        ``field_id`` (or ``RA`` and ``Dec``), ``obstime``, ``filter``, and
        ``exposure_time``; optional columns include ``airmass``,
        ``seeing``, ``limmag``, ``target_name``, and
        ``processed_fraction``. Ingestion runs asynchronously server-side.
    """
    payload = {
        "instrumentID": instrument_id,
        "observationData": observation_data,
    }
    unwrap(client.post("/api/observation/ascii", json=payload))


def fetch_observation_simsurvey(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    instrument_id: int,
    *,
    start_date: str,
    end_date: str,
    localization_dateobs: str,
    localization_name: str | None = None,
    localization_cumprob: float | None = None,
    number_injections: int | None = None,
    number_detections: int | None = None,
    detection_threshold: float | None = None,
    minimum_phase: float | None = None,
    maximum_phase: float | None = None,
    model_name: str | None = None,
    optional_injection_parameters: dict[str, Any] | None = None,
    group_ids: list[int] | None = None,
) -> ObservationSimSurveyResponse:
    """Start a SimSurvey efficiency calculation over executed observations.

    The analysis runs asynchronously server-side; the returned ID can be
    used with :func:`fetch_survey_efficiency_for_observations` and
    :func:`fetch_observation_simsurvey_plot`.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument whose observations to analyze.
    start_date, end_date : str
        Time range of observations to include, as ISO-format date strings.
    localization_dateobs : str
        GCN event time in ISO 8601 format identifying the localization.
    localization_name : str, optional
        Name of the localization / skymap to use. Defaults to the event's
        most recent localization.
    localization_cumprob : float, optional
        Cumulative probability up to which to include fields.
        Server default 0.95.
    number_injections : int, optional
        Number of simulations to evaluate efficiency with.
        Server default 1000.
    number_detections : int, optional
        Number of detections required for a detection. Server default 1.
    detection_threshold : float, optional
        Threshold (in sigmas) required for detection. Server default 5.
    minimum_phase, maximum_phase : float, optional
        Phase range (in days) post event time to consider detections.
        Server defaults 0 and 3.
    model_name : str, optional
        One of ``"kilonova"`` (server default), ``"afterglow"``, or
        ``"linear"``.
    optional_injection_parameters : dict, optional
        Extra injection parameters for the chosen model.
    group_ids : list of int, optional
        Groups that can view the analysis. Defaults to all of the token's
        groups.
    """
    params: dict[str, str | int | float] = {
        "startDate": start_date,
        "endDate": end_date,
        "localizationDateobs": localization_dateobs,
    }
    if localization_name is not None:
        params["localizationName"] = localization_name
    if localization_cumprob is not None:
        params["localizationCumprob"] = localization_cumprob
    if number_injections is not None:
        params["numberInjections"] = number_injections
    if number_detections is not None:
        params["numberDetections"] = number_detections
    if detection_threshold is not None:
        params["detectionThreshold"] = detection_threshold
    if minimum_phase is not None:
        params["minimumPhase"] = minimum_phase
    if maximum_phase is not None:
        params["maximumPhase"] = maximum_phase
    if model_name is not None:
        params["modelName"] = model_name
    if optional_injection_parameters is not None:
        params["optionalInjectionParameters"] = json.dumps(
            optional_injection_parameters
        )
    if group_ids is not None:
        params["group_ids"] = ",".join(str(gid) for gid in group_ids)
    response = client.get(f"/api/observation/simsurvey/{instrument_id}", params=params)
    return ObservationSimSurveyResponse.model_validate(unwrap(response))


def delete_observation_simsurvey(
    client: httpx.Client,
    survey_efficiency_analysis_id: int,
) -> None:
    """Delete a SimSurvey efficiency calculation.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    survey_efficiency_analysis_id : int
        ID of the survey efficiency analysis to delete.
    """
    unwrap(client.delete(f"/api/observation/simsurvey/{survey_efficiency_analysis_id}"))


def fetch_observation_simsurvey_plot(
    client: httpx.Client,
    survey_efficiency_analysis_id: int,
) -> bytes:
    """Download the summary plot (PDF) for a SimSurvey calculation.

    The analysis must have completed (its light curves must be available).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    survey_efficiency_analysis_id : int
        ID of the survey efficiency analysis to plot.
    """
    response = client.get(
        f"/api/observation/simsurvey/{survey_efficiency_analysis_id}/plot"
    )
    return unwrap_content(response)


def post_observation_treasuremap(  # noqa: PLR0913 -- mirrors the endpoint's parameters
    client: httpx.Client,
    instrument_id: int,
    *,
    start_date: str,
    end_date: str,
    localization_dateobs: str,
    localization_name: str | None = None,
    localization_cumprob: float | None = None,
    number_observations: int | None = None,
) -> None:
    """Submit an instrument's executed observations to treasuremap.space.

    Requires an allocation on the instrument with a
    ``TREASUREMAP_API_TOKEN`` in its alternative data.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument whose observations to submit.
    start_date, end_date : str
        Time range of observations to include, as ISO-format date strings.
    localization_dateobs : str
        GCN event time in ISO 8601 format identifying the localization.
    localization_name : str, optional
        Name of the localization / skymap to use.
    localization_cumprob : float, optional
        Cumulative probability up to which to include fields.
        Server default 0.95.
    number_observations : int, optional
        Minimum number of observations of a field required to include it.
        Server default 1.
    """
    payload: dict[str, str | float] = {
        "startDate": start_date,
        "endDate": end_date,
        "localizationDateobs": localization_dateobs,
    }
    if localization_name is not None:
        payload["localizationName"] = localization_name
    if localization_cumprob is not None:
        payload["localizationCumprob"] = localization_cumprob
    params: dict[str, int] = {}
    if number_observations is not None:
        params["numberObservations"] = number_observations
    unwrap(
        client.post(
            f"/api/observation/treasuremap/{instrument_id}",
            params=params,
            json=payload,
        )
    )


def delete_observation_treasuremap(
    client: httpx.Client,
    instrument_id: int,
    *,
    localization_dateobs: str,
) -> None:
    """Cancel an instrument's pointings on treasuremap.space for an event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument whose pointings to cancel.
    localization_dateobs : str
        GCN event time in ISO 8601 format identifying the event.
    """
    response = client.request(
        "DELETE",
        f"/api/observation/treasuremap/{instrument_id}",
        json={"localizationDateobs": localization_dateobs},
    )
    unwrap(response)


def post_observation_external_api(
    client: httpx.Client,
    allocation_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """Retrieve and ingest executed observations from an external API.

    The allocation's instrument must implement a remote observation plan
    API with retrieval support. Ingestion runs asynchronously server-side.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation whose instrument API to query.
    start_date, end_date : str, optional
        Time range to retrieve, as ISO-format date strings. Defaults to
        the last three days.
    """
    payload: dict[str, str | int] = {"allocation_id": allocation_id}
    if start_date is not None:
        payload["start_date"] = start_date
    if end_date is not None:
        payload["end_date"] = end_date
    unwrap(client.post("/api/observation/external_api", json=payload))


def fetch_observation_external_api(
    client: httpx.Client,
    allocation_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    queues_only: bool = False,
) -> ObservationQueuesResponse:
    """Retrieve queued observations from an external API.

    The allocation's instrument must implement a remote observation plan
    API with queue support. Unless ``queues_only`` is true, the queued
    observations are ingested asynchronously server-side and both dates
    are required.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation whose instrument API to query.
    start_date, end_date : str, optional
        Time range to retrieve, as ISO-format date strings. Required
        unless ``queues_only`` is true.
    queues_only : bool, optional
        Return the queue names only, without ingesting observations.
    """
    params: dict[str, str | bool] = {"queuesOnly": queues_only}
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    response = client.get(
        f"/api/observation/external_api/{allocation_id}", params=params
    )
    return ObservationQueuesResponse.model_validate(unwrap(response))


def delete_observation_external_api(
    client: httpx.Client,
    allocation_id: int,
    *,
    queue_name: str,
) -> None:
    """Delete a queue of observations via an external API.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation whose instrument API to use.
    queue_name : str
        Name of the queue to remove.
    """
    response = client.request(
        "DELETE",
        f"/api/observation/external_api/{allocation_id}",
        json={"queueName": queue_name},
    )
    unwrap(response)
