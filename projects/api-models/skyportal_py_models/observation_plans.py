"""Response models for ``/api/observation_plan``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import (
    EventObservationPlanResponse,
    EventObservationPlanStatisticsResponse,
    ObservationPlanRequestResponse,
    PlannedObservationResponse,
)
from skyportal_py_models.allocations import AllocationResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.users import UserResponse


class AllocationObservationPlansPageResponse(BaseModel):
    """One page of observation plan requests under an allocation."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    observation_plan_requests: list[ObservationPlanRequestResponse] = Field(
        default_factory=list
    )
    total_matches: int = Field(alias="totalMatches", default=0)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int | None = Field(alias="numPerPage", default=50)


class ObservationPlanRequestsPageResponse(BaseModel):
    """One page of results from an observation plan requests query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    requests: list[ObservationPlanRequestResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)


class ObservationPlanIdsResponse(BaseModel):
    """Result of submitting observation plan requests."""

    model_config = ConfigDict(extra="forbid")

    ids: list[int] = Field(default_factory=list)


class ObservationPlanGeoJSONResponse(BaseModel):
    """GeoJSON contours of the fields of an observation plan."""

    model_config = ConfigDict(extra="forbid")

    geojson: list[dict[str, Any]] = Field(default_factory=list)


class ObservationPlanSimSurveyResponse(BaseModel):
    """Result of starting a simsurvey efficiency analysis."""

    model_config = ConfigDict(extra="forbid")

    id: int


class DefaultSurveyEfficiencyRequestResponse(BaseModel):
    """A default efficiency request attached to a default observation plan."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    default_observationplan_request_id: int | None = None
    default_observationplan_request: DefaultObservationPlanRequestResponse | None = None


class DefaultObservationPlanRequestResponse(BaseModel):
    """A default observation plan request."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    requester_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    filters: dict[str, Any] | None = None
    allocation_id: int | None = None
    default_plan_name: str | None = None
    auto_send: bool | None = None
    allocation: AllocationResponse | None = None
    requester: UserResponse | None = None
    target_groups: list[GroupResponse] = Field(default_factory=list)
    default_survey_efficiencies: list[DefaultSurveyEfficiencyRequestResponse] = Field(
        default_factory=list
    )


__all__ = [
    "AllocationObservationPlansPageResponse",
    "DefaultObservationPlanRequestResponse",
    "DefaultSurveyEfficiencyRequestResponse",
    "EventObservationPlanResponse",
    "EventObservationPlanStatisticsResponse",
    "ObservationPlanGeoJSONResponse",
    "ObservationPlanIdsResponse",
    "ObservationPlanRequestResponse",
    "ObservationPlanRequestsPageResponse",
    "ObservationPlanSimSurveyResponse",
    "PlannedObservationResponse",
]
DefaultSurveyEfficiencyRequestResponse.model_rebuild()
