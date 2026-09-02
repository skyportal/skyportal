"""Response models for ``/api/observation_plan``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

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


class ObservationPlanPost(BaseModel):
    """Payload for submitting an observation plan request."""

    model_config = ConfigDict(extra="forbid")

    gcnevent_id: int
    allocation_id: int
    localization_id: int
    payload: dict[str, Any]
    status: str | None = None
    target_group_ids: list[int] | None = None
    requester_id: int | None = None


class ObservationPlanManualPost(BaseModel):
    """Payload for submitting a manually-built observation plan."""

    model_config = ConfigDict(extra="forbid")

    allocation_id: int
    plan_name: str
    status: str
    payload: dict[str, Any]
    observation_plans: list[dict[str, Any]]
    gcnevent_id: int | None = None
    dateobs: str | None = None
    localization_id: int | None = None
    localization_name: str | None = None


class DefaultObservationPlanPost(BaseModel):
    """Payload for creating a default observation plan request."""

    model_config = ConfigDict(extra="forbid")

    allocation_id: int
    default_plan_name: str
    payload: dict[str, Any]
    auto_send: bool | None = None
    filters: dict[str, Any] | None = None
    target_group_ids: list[int] | None = None
    requester_id: int | None = None


MAX_OBSERVATION_PLAN_REQUESTS = 1000


class ObservationPlanRequestGetQuery(BaseModel):
    """Query parameters for retrieving observation plan requests."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset(
        {"includePlannedObservations", "rubinFormat"}
    )

    includePlannedObservations: bool = Field(
        default=False,
        description="Boolean indicating whether to include associated planned observations. Defaults to false.",
    )
    rubinFormat: bool = Field(
        default=False,
        description="Boolean indicating whether to format the response in a way that is compatible with Rubin",
    )
    dateobs: str | None = Field(
        default=None,
        description="GcnEvent dateobs to filter on",
    )
    instrumentID: int | None = Field(
        default=None,
        description="Instrument ID to filter on",
    )
    startDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by created_at >= startDate",
    )
    endDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by created_at <= endDate",
    )
    status: str | None = Field(
        default=None,
        description="String to match status of request against",
    )
    numPerPage: int = Field(
        default=100,
        description=f"Number of observation plan requests to return per paginated request. Defaults to 100. Can be no larger than {MAX_OBSERVATION_PLAN_REQUESTS}.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1",
    )


class ObservationPlanRequestPostBody(BaseModel):
    """Request body for submitting one or more observation plan requests.

    Accepts either a single plan (the plan fields at the top level) or a
    `observation_plans` list together with `combine_plans`.
    """

    model_config = ConfigDict(extra="forbid")

    observation_plans: list[dict] | None = Field(
        None, description="List of observation plan requests to submit."
    )
    combine_plans: bool = Field(
        False,
        description="Whether to combine the submitted plans into a single request.",
    )
    gcnevent_id: int | None = Field(None, description="ID of the GcnEvent.")
    payload: dict | None = Field(
        None, description="Content of the observation plan request."
    )
    status: str | None = Field(None, description="The status of the request.")
    allocation_id: int | None = Field(
        None, description="Observation plan request allocation ID."
    )
    localization_id: int | None = Field(None, description="Localization ID.")
    target_group_ids: list[int] | None = Field(
        None,
        description=(
            "IDs of groups to share the results of the observation plan request with."
        ),
    )
    requester_id: int | None = Field(
        None, description="ID of the user making the request."
    )


class ObservationPlanRequestPostResponse(BaseModel):
    """Data payload returned when submitting observation plan requests."""

    ids: list[int] = Field(description="New observation plan request IDs")


class ObservationPlanManualPostBody(BaseModel):
    """Request body for submitting a manual observation plan request."""

    model_config = ConfigDict(extra="forbid")

    gcnevent_id: int | None = Field(None, description="ID of the GcnEvent.")
    dateobs: str | None = Field(
        None,
        description="UTC event timestamp, used to look up the GcnEvent when gcnevent_id is not provided.",
    )
    localization_id: int | None = Field(None, description="Localization ID.")
    localization_name: str | None = Field(
        None,
        description="Name of the localization, used to look it up when localization_id is not provided.",
    )
    allocation_id: int | None = Field(
        None, description="Observation plan request allocation ID."
    )
    status: str | None = Field(None, description="The status of the request.")
    payload: dict | None = Field(
        None, description="Content of the observation plan request."
    )
    plan_name: str | None = Field(None, description="Name of the observation plan.")
    observation_plans: list[dict] | None = Field(
        None,
        description="Observation plans, each with its validity window and planned observations.",
    )


class ObservationPlanManualPostResponse(BaseModel):
    """Data payload returned when submitting a manual observation plan request."""

    id: int = Field(description="New observation plan request ID")


class ObservationPlanNameGetQuery(BaseModel):
    """Query parameters for retrieving observation plan names."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        description="The name of the Observation Plan",
    )


class ObservationPlanFieldsDeleteBody(BaseModel):
    """Request body for removing fields from an observation plan."""

    model_config = ConfigDict(extra="forbid")

    fieldIds: list[int] | None = Field(
        None, description="List of field IDs to remove from the plan"
    )


class ObservationPlanPlotGetQuery(BaseModel):
    """Query parameters for the worldmap and observability plots."""

    model_config = ConfigDict(extra="forbid")

    maxAirmass: float = Field(
        default=2.5,
        description="Maximum airmass to consider. Defaults to 2.5.",
    )
    twilight: Literal["astronomical", "nautical", "civil"] = Field(
        default="astronomical",
        description="Twilight definition. Choices are astronomical (-18 degrees), nautical (-12 degrees), and civil (-6 degrees).",
    )


class ObservationPlanCreateObservingRunPostBody(BaseModel):
    """Request body for creating an observing run from an observation plan."""

    model_config = ConfigDict(extra="forbid")

    groupIds: list[int] | None = Field(
        None,
        description=(
            "IDs of the groups to share the created sources with. "
            "Defaults to the allocation's group."
        ),
    )


class ObservationPlanSimSurveyGetQuery(BaseModel):
    """Query parameters for running a simsurvey efficiency analysis."""

    model_config = ConfigDict(extra="forbid")

    numberInjections: int = Field(
        default=1000,
        description="Number of simulations to evaluate efficiency with. Defaults to 1000.",
    )
    numberDetections: int = Field(
        default=1,
        description="Number of detections required for detection. Defaults to 1.",
    )
    detectionThreshold: float = Field(
        default=5.0,
        description="Threshold (in sigmas) required for detection. Defaults to 5.",
    )
    minimumPhase: float = Field(
        default=0.0,
        description="Minimum phase (in days) post event time to consider detections. Defaults to 0.",
    )
    maximumPhase: float = Field(
        default=3.0,
        description="Maximum phase (in days) post event time to consider detections. Defaults to 3.",
    )
    modelName: str = Field(
        default="kilonova",
        description="Model to simulate efficiency for. Must be one of kilonova, afterglow, or linear. Defaults to kilonova.",
    )
    optionalInjectionParameters: str = Field(
        default="{}",
        description="JSON-encoded object of optional parameters to specify the injection type, along with a list of possible values (to be used in a dropdown UI)",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be able to view the analyses. Defaults to all of requesting user's groups.",
    )


class DefaultObservationPlanPostBody(BaseModel):
    """Request body for creating a default observation plan request."""

    model_config = ConfigDict(extra="forbid")

    allocation_id: int | None = Field(
        None, description="Observation plan request allocation ID."
    )
    default_plan_name: str | None = Field(
        None, description="Unique name of the default observation plan."
    )
    payload: dict | None = Field(
        None, description="Content of the default observation plan request."
    )
    target_group_ids: list[int] | None = Field(
        None,
        description=(
            "IDs of groups to share the results of the default observation plan request with."
        ),
    )
    filters: dict | None = Field(
        None,
        description=(
            "Filters to determine which of the default observation plan requests get executed for which events."
        ),
    )
    auto_send: bool | None = Field(
        None, description="Automatically send to telescope queue?"
    )
    requester_id: int | None = Field(
        None, description="ID of the user making the request."
    )


class DefaultObservationPlanPostResponse(BaseModel):
    """Data payload returned when creating a default observation plan request."""

    id: int = Field(description="New default observation plan request ID")


__all__ = [
    "MAX_OBSERVATION_PLAN_REQUESTS",
    "ObservationPlanRequestGetQuery",
    "ObservationPlanRequestPostBody",
    "ObservationPlanRequestPostResponse",
    "ObservationPlanManualPostBody",
    "ObservationPlanManualPostResponse",
    "ObservationPlanNameGetQuery",
    "ObservationPlanFieldsDeleteBody",
    "ObservationPlanPlotGetQuery",
    "ObservationPlanCreateObservingRunPostBody",
    "ObservationPlanSimSurveyGetQuery",
    "DefaultObservationPlanPostBody",
    "DefaultObservationPlanPostResponse",
    "ObservationPlanPost",
    "ObservationPlanManualPost",
    "DefaultObservationPlanPost",
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
