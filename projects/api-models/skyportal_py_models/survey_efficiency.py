"""Response models for ``/api/survey_efficiency``."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import (
    SurveyEfficiencyForObservationPlanResponse,
    SurveyEfficiencyForObservationsResponse,
)


class SurveyEfficiencyForObservationPlanGetQuery(BaseModel):
    """Query parameters for listing observation plan efficiency analyses."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    observation_plan_id: int | None = Field(
        default=None,
        description="EventObservationPlan ID to retrieve observation plan efficiency analyses for",
    )


class DefaultSurveyEfficiencyPostBody(BaseModel):
    """Request body for creating a default survey efficiency request."""

    model_config = ConfigDict(extra="forbid")

    default_observationplan_request_id: int = Field(
        description="Default observation plan request ID."
    )
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Content of the default survey efficiency analysis.",
    )


class DefaultSurveyEfficiencyPostResponse(BaseModel):
    """Data payload returned when creating a default survey efficiency request."""

    id: int = Field(description="New default survey efficiency request ID")


class SurveyEfficiencyForObservationsGetQuery(BaseModel):
    """Query parameters for listing observation efficiency analyses."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    gcnevent_id: int | None = Field(
        default=None,
        description="GcnEvent ID to retrieve observation efficiency analyses for",
    )


__all__ = [
    "SurveyEfficiencyForObservationPlanGetQuery",
    "DefaultSurveyEfficiencyPostBody",
    "DefaultSurveyEfficiencyPostResponse",
    "SurveyEfficiencyForObservationsGetQuery",
    "SurveyEfficiencyForObservationPlanResponse",
    "SurveyEfficiencyForObservationsResponse",
]
