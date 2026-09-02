"""Typed endpoint functions for ``/api/survey_efficiency``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models._cyclic import (
    SurveyEfficiencyForObservationPlanResponse,
    SurveyEfficiencyForObservationsResponse,
)
from skyportal_py_models.observation_plans import DefaultSurveyEfficiencyRequestResponse
from skyportal_py_models.survey_efficiency import DefaultSurveyEfficiencyPostResponse

from skyportal_py._http import unwrap

__all__ = [
    "DefaultSurveyEfficiencyPostResponse",
    "DefaultSurveyEfficiencyRequestResponse",
    "SurveyEfficiencyForObservationPlanResponse",
    "SurveyEfficiencyForObservationsResponse",
]


def fetch_survey_efficiency_for_observations(
    client: httpx.Client,
    survey_efficiency_analysis_id: int,
) -> SurveyEfficiencyForObservationsResponse:
    """Retrieve a single survey efficiency analysis of executed observations.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    survey_efficiency_analysis_id : int
        ID of the analysis, as returned by
        :func:`skyportal_py.observations.post_observation_simsurvey`.
    """
    response = client.get(
        f"/api/survey_efficiency/observations/{survey_efficiency_analysis_id}"
    )
    return SurveyEfficiencyForObservationsResponse.model_validate(unwrap(response))


def fetch_survey_efficiencies_for_observations(
    client: httpx.Client,
    *,
    gcnevent_id: int | None = None,
) -> list[SurveyEfficiencyForObservationsResponse]:
    """Retrieve the survey efficiency analyses of executed observations.

    Only analyses visible to the requesting user's groups are returned.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    gcnevent_id : int, optional
        Only return analyses for this GCN event. If omitted, analyses for
        all accessible events are returned.
    """
    params: dict[str, int] = {}
    if gcnevent_id is not None:
        params["gcnevent_id"] = gcnevent_id
    response = client.get("/api/survey_efficiency/observations", params=params)
    return [
        SurveyEfficiencyForObservationsResponse.model_validate(analysis)
        for analysis in unwrap(response)
    ]


def fetch_survey_efficiency_for_observation_plan(
    client: httpx.Client,
    survey_efficiency_analysis_id: int,
) -> SurveyEfficiencyForObservationPlanResponse:
    """Retrieve a single survey efficiency analysis of an observation plan.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    survey_efficiency_analysis_id : int
        ID of the analysis, as returned by
        :func:`skyportal_py.observation_plans.fetch_observation_plan_simsurvey`.
    """
    response = client.get(
        f"/api/survey_efficiency/observation_plan/{survey_efficiency_analysis_id}"
    )
    return SurveyEfficiencyForObservationPlanResponse.model_validate(unwrap(response))


def fetch_survey_efficiencies_for_observation_plan(
    client: httpx.Client,
    *,
    observation_plan_id: int | None = None,
) -> list[SurveyEfficiencyForObservationPlanResponse]:
    """Retrieve the survey efficiency analyses of observation plans.

    Only analyses visible to the requesting user's groups are returned.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observation_plan_id : int, optional
        Only return analyses for this event observation plan (the
        generated plan, not the observation plan request). If omitted,
        all accessible analyses are returned.
    """
    params: dict[str, int] = {}
    if observation_plan_id is not None:
        params["observation_plan_id"] = observation_plan_id
    response = client.get("/api/survey_efficiency/observation_plan", params=params)
    return [
        SurveyEfficiencyForObservationPlanResponse.model_validate(analysis)
        for analysis in unwrap(response)
    ]


def post_default_survey_efficiency(
    client: httpx.Client,
    default_observationplan_request_id: int,
    *,
    payload: dict[str, Any] | None = None,
) -> DefaultSurveyEfficiencyPostResponse:
    """Create a default survey efficiency request.

    The analysis is run automatically whenever the referenced default
    observation plan generates a plan.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    default_observationplan_request_id : int
        ID of the default observation plan request to attach the analysis
        to. It must be readable by the requesting user.
    payload : dict, optional
        Content of the survey efficiency analysis (simulation parameters
        such as ``numberInjections``, ``numberDetections``,
        ``detectionThreshold`` and ``modelName``).
    """
    body: dict[str, Any] = {
        "default_observationplan_request_id": default_observationplan_request_id
    }
    if payload is not None:
        body["payload"] = payload
    response = client.post("/api/default_survey_efficiency", json=body)
    return DefaultSurveyEfficiencyPostResponse.model_validate(unwrap(response))


def fetch_default_survey_efficiency(
    client: httpx.Client,
    default_survey_efficiency_id: int,
) -> DefaultSurveyEfficiencyRequestResponse:
    """Retrieve a single default survey efficiency request by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    default_survey_efficiency_id : int
        ID of the default survey efficiency request.
    """
    response = client.get(
        f"/api/default_survey_efficiency/{default_survey_efficiency_id}"
    )
    return DefaultSurveyEfficiencyRequestResponse.model_validate(unwrap(response))


def fetch_default_survey_efficiencies(
    client: httpx.Client,
) -> list[DefaultSurveyEfficiencyRequestResponse]:
    """Retrieve all accessible default survey efficiency requests.

    Each request includes its parent default observation plan request
    under ``default_observationplan_request``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/default_survey_efficiency")
    return [
        DefaultSurveyEfficiencyRequestResponse.model_validate(request)
        for request in unwrap(response)
    ]


def delete_default_survey_efficiency(
    client: httpx.Client,
    default_survey_efficiency_id: int,
) -> None:
    """Delete a default survey efficiency request.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    default_survey_efficiency_id : int
        ID of the default survey efficiency request to delete.
    """
    unwrap(
        client.delete(f"/api/default_survey_efficiency/{default_survey_efficiency_id}")
    )
