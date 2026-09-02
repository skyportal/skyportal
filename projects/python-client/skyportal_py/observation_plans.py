"""Typed endpoint functions for ``/api/observation_plan``."""

from __future__ import annotations

import json
from typing import Any

import httpx
from skyportal_py_models._cyclic import (
    EventObservationPlanResponse,
    EventObservationPlanStatisticsResponse,
    ObservationPlanRequestResponse,
    PlannedObservationResponse,
)
from skyportal_py_models.observation_plans import (
    AllocationObservationPlansPageResponse,
    DefaultObservationPlanPost,
    DefaultObservationPlanPostResponse,
    DefaultObservationPlanRequestResponse,
    DefaultSurveyEfficiencyRequestResponse,
    ObservationPlanGeoJSONResponse,
    ObservationPlanIdsResponse,
    ObservationPlanManualPost,
    ObservationPlanManualPostResponse,
    ObservationPlanPost,
    ObservationPlanRequestsPageResponse,
    ObservationPlanSimSurveyResponse,
)

from skyportal_py._http import unwrap, unwrap_content
from skyportal_py.survey_efficiency import SurveyEfficiencyForObservationPlanResponse

__all__ = [
    "AllocationObservationPlansPageResponse",
    "DefaultObservationPlanPost",
    "DefaultObservationPlanPostResponse",
    "DefaultObservationPlanRequestResponse",
    "DefaultSurveyEfficiencyRequestResponse",
    "EventObservationPlanResponse",
    "EventObservationPlanStatisticsResponse",
    "ObservationPlanGeoJSONResponse",
    "ObservationPlanIdsResponse",
    "ObservationPlanManualPost",
    "ObservationPlanManualPostResponse",
    "ObservationPlanPost",
    "ObservationPlanRequestResponse",
    "ObservationPlanRequestsPageResponse",
    "ObservationPlanSimSurveyResponse",
    "PlannedObservationResponse",
]


def post_observation_plan(
    client: httpx.Client,
    payload: ObservationPlanPost,
) -> ObservationPlanIdsResponse:
    """Submit an observation plan request.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ObservationPlanPost
        The request to submit. ``payload`` must contain a globally unique
        ``queue_name`` key and a ``filters`` key that is a subset of the
        allocation instrument's filters; the allocation's instrument API
        defines the rest of its schema. The plan is generated
        asynchronously server-side.
    """
    response = client.post(
        "/api/observation_plan", json=payload.model_dump(exclude_none=True)
    )
    return ObservationPlanIdsResponse.model_validate(unwrap(response))


def post_observation_plans(
    client: httpx.Client,
    payloads: list[ObservationPlanPost],
    *,
    combine_plans: bool = False,
) -> ObservationPlanIdsResponse:
    """Submit several observation plan requests in one call.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payloads : list of ObservationPlanPost
        The requests to submit. Each ``payload`` must contain a unique
        ``queue_name`` key and a valid ``filters`` key.
    combine_plans : bool, optional
        Generate the plans jointly (combined) instead of independently.
    """
    body = {
        "observation_plans": [p.model_dump(exclude_none=True) for p in payloads],
        "combine_plans": combine_plans,
    }
    response = client.post("/api/observation_plan", json=body)
    return ObservationPlanIdsResponse.model_validate(unwrap(response))


def fetch_observation_plan(
    client: httpx.Client,
    observation_plan_request_id: int,
    *,
    include_planned_observations: bool = False,
    rubin_format: bool = False,
) -> ObservationPlanRequestResponse | dict[str, Any]:
    """Retrieve a single observation plan request by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request.
    include_planned_observations : bool, optional
        Include the planned observations (with fields and rise/set
        times) of each associated observation plan.
    rubin_format : bool, optional
        Return the first observation plan converted to Rubin-compatible
        format instead of an :class:`ObservationPlanRequestResponse`. Only takes
        effect when ``include_planned_observations`` is true.
    """
    params: dict[str, bool] = {}
    if include_planned_observations:
        params["includePlannedObservations"] = True
    if rubin_format:
        params["rubinFormat"] = True
    response = client.get(
        f"/api/observation_plan/{observation_plan_request_id}", params=params
    )
    data = unwrap(response)
    if rubin_format and include_planned_observations:
        return data
    return ObservationPlanRequestResponse.model_validate(data)


def fetch_observation_plans(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 100,
    dateobs: str | None = None,
    instrument_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str | None = None,
    include_planned_observations: bool = False,
) -> ObservationPlanRequestsPageResponse:
    """Query observation plan requests, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls; the server caps the page size.
    dateobs : str, optional
        Restrict to plans for the GCN event with this ``dateobs``.
    instrument_id : int, optional
        Restrict to plans whose allocation uses this instrument.
    start_date, end_date : str, optional
        Restrict to requests created in this date range, as
        arrow-parseable date strings, e.g. ``"2020-01-01"``.
    status : str, optional
        Restrict to requests whose status contains this string.
    include_planned_observations : bool, optional
        Include the planned observations of each observation plan.
    """
    params: dict[str, str | int | bool] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if dateobs is not None:
        params["dateobs"] = dateobs
    if instrument_id is not None:
        params["instrumentID"] = instrument_id
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    if status is not None:
        params["status"] = status
    if include_planned_observations:
        params["includePlannedObservations"] = True
    response = client.get("/api/observation_plan", params=params)
    return ObservationPlanRequestsPageResponse.model_validate(unwrap(response))


def delete_observation_plan(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> None:
    """Delete an observation plan request.

    Plans already submitted to the telescope queue cannot be deleted.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request to delete.
    """
    unwrap(client.delete(f"/api/observation_plan/{observation_plan_request_id}"))


def post_observation_plan_manual(
    client: httpx.Client,
    payload: ObservationPlanManualPost,
) -> ObservationPlanManualPostResponse:
    """Submit a manually-built observation plan.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ObservationPlanManualPost
        The plan to submit. Provide either ``gcnevent_id`` or ``dateobs``
        to identify the GCN event, and either ``localization_id`` or
        ``localization_name`` to identify the localization. Only the
        first entry of ``observation_plans`` is used; it must contain
        ``validity_window_start``, ``validity_window_end``, ``status``
        and a ``planned_observations`` list whose entries each contain
        ``dateobs``, ``field_id``, ``exposure_time``, ``weight``,
        ``filt``, ``planned_observation_id`` and
        ``overhead_per_exposure``.
    """
    response = client.post(
        "/api/observation_plan/manual",
        json=payload.model_dump(exclude_none=True),
    )
    return ObservationPlanManualPostResponse.model_validate(unwrap(response))


def fetch_observation_plan_names(client: httpx.Client) -> list[str]:
    """Retrieve all distinct observation plan names.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/observation_plan/plan_names")
    return [str(name) for name in unwrap(response)]


def fetch_observation_plan_name_exists(client: httpx.Client, name: str) -> bool:
    """Check whether an observation plan name is already in use.

    Also matches queue names of pending observation plan requests.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str
        The plan name to check.
    """
    response = client.get("/api/observation_plan/plan_names", params={"name": name})
    return bool(unwrap(response)["exists"])


def post_observation_plan_treasuremap(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> None:
    """Submit an observation plan's pointings to treasuremap.space.

    Requires a ``TREASUREMAP_API_TOKEN`` in the allocation's ``altdata``
    and a TreasureMap instrument ID on the instrument.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request to submit.
    """
    unwrap(
        client.post(f"/api/observation_plan/{observation_plan_request_id}/treasuremap")
    )


def delete_observation_plan_treasuremap(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> None:
    """Remove an observation plan's pointings from treasuremap.space.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request whose pointings to cancel.
    """
    unwrap(
        client.delete(
            f"/api/observation_plan/{observation_plan_request_id}/treasuremap"
        )
    )


def fetch_observation_plan_gcn(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> str:
    """Retrieve a GCN-circular-style text summary of an observation plan.

    Requires the plan to have computed statistics.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request to summarize.
    """
    response = client.get(f"/api/observation_plan/{observation_plan_request_id}/gcn")
    return str(unwrap(response))


def post_observation_plan_queue(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> ObservationPlanRequestResponse | None:
    """Submit an observation plan request to the telescope queue.

    The plan must have status ``"complete"`` and at least one planned
    observation; otherwise the server returns no data.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request to submit.
    """
    response = client.post(f"/api/observation_plan/{observation_plan_request_id}/queue")
    data = unwrap(response)
    if data is None:
        return None
    return ObservationPlanRequestResponse.model_validate(data)


def delete_observation_plan_queue(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> ObservationPlanRequestResponse:
    """Remove an observation plan request from the telescope queue.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request to remove from the queue.
    """
    response = client.delete(
        f"/api/observation_plan/{observation_plan_request_id}/queue"
    )
    return ObservationPlanRequestResponse.model_validate(unwrap(response))


def fetch_observation_plan_movie(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> bytes:
    """Download an animated GIF of an observation plan's coverage.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request to animate.
    """
    response = client.get(f"/api/observation_plan/{observation_plan_request_id}/movie")
    return unwrap_content(response)


def fetch_observation_plan_simsurvey(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    observation_plan_request_id: int,
    *,
    number_of_injections: int = 1000,
    number_of_detections: int = 1,
    detection_threshold: float = 5,
    minimum_phase: float = 0,
    maximum_phase: float = 3,
    model_name: str = "kilonova",
    optional_injection_parameters: dict[str, Any] | None = None,
    group_ids: list[int] | None = None,
) -> ObservationPlanSimSurveyResponse:
    """Start a simsurvey efficiency analysis for an observation plan.

    The analysis runs asynchronously server-side; the returned ID
    identifies the resulting survey efficiency analysis.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request to analyze.
    number_of_injections : int, optional
        Number of simulated transients to inject.
    number_of_detections : int, optional
        Number of detections required to count a transient as detected.
    detection_threshold : float, optional
        Detection threshold in sigmas.
    minimum_phase, maximum_phase : float, optional
        Phase range (days post event) in which to consider detections.
    model_name : str, optional
        Model to simulate; one of ``"kilonova"``, ``"afterglow"`` or
        ``"linear"``.
    optional_injection_parameters : dict, optional
        Extra model-specific injection parameters, JSON-encoded into the
        query string.
    group_ids : list of int, optional
        Groups that may view the analysis. Defaults to all of the
        token's groups.
    """
    params: dict[str, str | int | float] = {
        "numberInjections": number_of_injections,
        "numberDetections": number_of_detections,
        "detectionThreshold": detection_threshold,
        "minimumPhase": minimum_phase,
        "maximumPhase": maximum_phase,
        "modelName": model_name,
    }
    if optional_injection_parameters is not None:
        params["optionalInjectionParameters"] = json.dumps(
            optional_injection_parameters
        )
    if group_ids is not None:
        params["group_ids"] = ",".join(str(gid) for gid in group_ids)
    response = client.get(
        f"/api/observation_plan/{observation_plan_request_id}/simsurvey",
        params=params,
    )
    return ObservationPlanSimSurveyResponse.model_validate(unwrap(response))


def delete_observation_plan_simsurvey(
    client: httpx.Client,
    survey_efficiency_analysis_id: int,
) -> None:
    """Delete a simsurvey efficiency analysis.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    survey_efficiency_analysis_id : int
        ID of the survey efficiency analysis (not the observation plan
        request) to delete.
    """
    unwrap(
        client.delete(
            f"/api/observation_plan/{survey_efficiency_analysis_id}/simsurvey"
        )
    )


def fetch_observation_plan_simsurvey_plot(
    client: httpx.Client,
    survey_efficiency_analysis_id: int,
) -> bytes:
    """Download a PDF summary plot of a simsurvey efficiency analysis.

    The analysis must have completed (light curves available).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    survey_efficiency_analysis_id : int
        ID of the survey efficiency analysis (not the observation plan
        request) to plot.
    """
    response = client.get(
        f"/api/observation_plan/{survey_efficiency_analysis_id}/simsurvey/plot"
    )
    return unwrap_content(response)


def fetch_observation_plan_geojson(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> ObservationPlanGeoJSONResponse:
    """Retrieve the GeoJSON field contours of an observation plan.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request.
    """
    response = client.get(
        f"/api/observation_plan/{observation_plan_request_id}/geojson"
    )
    return ObservationPlanGeoJSONResponse.model_validate(unwrap(response))


def fetch_observation_plan_survey_efficiency(
    client: httpx.Client,
    observation_plan_request_id: int,
) -> list[SurveyEfficiencyForObservationPlanResponse]:
    """Retrieve the survey efficiency analyses of an observation plan.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request.
    """
    response = client.get(
        f"/api/observation_plan/{observation_plan_request_id}/survey_efficiency"
    )
    return [
        SurveyEfficiencyForObservationPlanResponse.model_validate(analysis)
        for analysis in unwrap(response)
    ]


def post_observation_plan_observing_run(
    client: httpx.Client,
    observation_plan_request_id: int,
    *,
    group_ids: list[int] | None = None,
) -> None:
    """Create an observing run from an observation plan's fields.

    Each planned field is saved as a source and assigned to a new
    observing run on the allocation's instrument.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request.
    group_ids : list of int, optional
        Groups to save the field sources to. Defaults to the
        allocation's group.
    """
    body: dict[str, list[int]] = {}
    if group_ids is not None:
        body["groupIds"] = group_ids
    unwrap(
        client.post(
            f"/api/observation_plan/{observation_plan_request_id}/observing_run",
            json=body,
        )
    )


def delete_observation_plan_fields(
    client: httpx.Client,
    observation_plan_request_id: int,
    field_ids: list[int],
) -> None:
    """Delete selected fields from an observation plan.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_request_id : int
        ID of the observation plan request.
    field_ids : list of int
        Database IDs of the fields whose planned observations to remove.
    """
    unwrap(
        client.request(
            "DELETE",
            f"/api/observation_plan/{observation_plan_request_id}/fields",
            json={"fieldIds": field_ids},
        )
    )


def post_default_observation_plan(
    client: httpx.Client,
    payload: DefaultObservationPlanPost,
) -> DefaultObservationPlanPostResponse:
    """Create a default observation plan request.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : DefaultObservationPlanPost
        The default plan to create. ``default_plan_name`` must be
        unique. ``payload`` must not contain ``start_date``,
        ``end_date`` or ``queue_name`` (the server fills these in per
        event). ``filters`` controls which GCN events trigger the plan
        and is required when ``auto_send`` is true.
    """
    response = client.post(
        "/api/default_observation_plan",
        json=payload.model_dump(exclude_none=True),
    )
    return DefaultObservationPlanPostResponse.model_validate(unwrap(response))


def fetch_default_observation_plan(
    client: httpx.Client,
    default_observation_plan_id: int,
) -> DefaultObservationPlanRequestResponse:
    """Retrieve a single default observation plan request by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    default_observation_plan_id : int
        ID of the default observation plan request.
    """
    response = client.get(
        f"/api/default_observation_plan/{default_observation_plan_id}"
    )
    return DefaultObservationPlanRequestResponse.model_validate(unwrap(response))


def fetch_default_observation_plans(
    client: httpx.Client,
) -> list[DefaultObservationPlanRequestResponse]:
    """Retrieve all default observation plan requests.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/default_observation_plan")
    return [
        DefaultObservationPlanRequestResponse.model_validate(request)
        for request in unwrap(response)
    ]


def delete_default_observation_plan(
    client: httpx.Client,
    default_observation_plan_id: int,
) -> None:
    """Delete a default observation plan request.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    default_observation_plan_id : int
        ID of the default observation plan request to delete.
    """
    unwrap(
        client.delete(f"/api/default_observation_plan/{default_observation_plan_id}")
    )


def fetch_allocation_observation_plans(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    allocation_id: int,
    *,
    page_number: int = 1,
    num_per_page: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "asc",
) -> AllocationObservationPlansPageResponse:
    """Retrieve the observation plan requests under an allocation.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation.
    page_number, num_per_page : int, optional
        Pagination controls; the server caps the page size.
    sort_by : str, optional
        Field to sort by; one of ``"created_at"``, ``"modified"``,
        ``"status"`` or ``"gcnevent_id"``.
    sort_order : str, optional
        ``"asc"`` or ``"desc"``.
    """
    params: dict[str, str | int] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    response = client.get(
        f"/api/allocation/observation_plans/{allocation_id}", params=params
    )
    return AllocationObservationPlansPageResponse.model_validate(unwrap(response))
