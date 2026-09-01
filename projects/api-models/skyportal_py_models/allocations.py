"""Response models for ``/api/allocation``."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import AllocationResponse, AllocationUserResponse
from skyportal_py_models.followup_requests import MAX_FOLLOWUP_REQUESTS


class AllocationPost(BaseModel):
    """Payload for creating an allocation."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    instrument_id: int
    group_id: int
    hours_allocated: float
    pi: str | None = None
    proposal_id: str | None = None
    types: list[str] | None = None
    validity_ranges: list[dict[str, Any]] | None = None
    default_share_group_ids: list[int] | None = None
    allocation_admin_ids: list[int] | None = None
    altdata: dict[str, Any] | None = Field(alias="_altdata", default=None)


class AllocationUpdate(BaseModel):
    """Payload for updating an allocation; every field is optional."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    instrument_id: int | None = None
    group_id: int | None = None
    hours_allocated: float | None = None
    pi: str | None = None
    proposal_id: str | None = None
    types: list[str] | None = None
    validity_ranges: list[dict[str, Any]] | None = None
    default_share_group_ids: list[int] | None = None
    allocation_admin_ids: list[int] | None = None
    altdata: dict[str, Any] | None = Field(alias="_altdata", default=None)
    replace_altdata: bool | None = None


MAX_OBSERVATION_PLANS = 1000


class AllocationObservationPlanGetQuery(BaseModel):
    """Query parameters for listing an allocation's observation plans."""

    model_config = ConfigDict(extra="forbid")

    numPerPage: int = Field(
        default=50,
        le=MAX_OBSERVATION_PLANS,
        description=(
            "Number of observation plans to return per paginated request. "
            f"Defaults to 50. Can be no larger than {MAX_OBSERVATION_PLANS}."
        ),
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    sortBy: Literal["created_at", "modified", "status", "gcnevent_id"] = Field(
        default="created_at",
        description="The field to sort by. Defaults to created_at.",
    )
    sortOrder: Literal["asc", "desc"] = Field(
        default="asc",
        description="The sort order, either asc or desc. Defaults to asc.",
    )


class AllocationPostBody(BaseModel):
    """Request body for creating an allocation."""

    model_config = ConfigDict(extra="forbid")

    group_id: int | None = Field(
        default=None,
        description="The ID of the Group the allocation is associated with.",
    )
    instrument_id: int | None = Field(
        default=None,
        description="The ID of the Instrument the allocation is associated with.",
    )
    pi: str | None = Field(
        default=None, description="The PI of the allocation's proposal."
    )
    proposal_id: str | None = Field(
        default=None,
        description="The ID of the proposal associated with this allocation.",
    )
    hours_allocated: float | None = Field(
        default=None, description="The number of hours allocated."
    )
    validity_ranges: list | None = Field(
        default=None,
        description="A list of validity ranges for the allocation, each with a "
        "start_date and end_date in UTC.",
    )
    types: list[str] | None = Field(
        default=None, description="The type(s) of allocation."
    )
    default_share_group_ids: list[int] | None = Field(
        default=None, description="List of default group IDs to share data with."
    )
    allocation_admin_ids: list[int] | None = Field(
        default=None, description="List of user IDs to set as allocation admins."
    )
    altdata: dict[str, Any] | str | None = Field(
        default=None,
        alias="_altdata",
        description="Additional metadata for the allocation (e.g., API credentials).",
    )


class AllocationPutBody(AllocationPostBody):
    """Request body for updating an allocation."""

    replace_altdata: bool | None = Field(
        default=None,
        description="Whether to replace existing altdata rather than merge into it.",
    )


class AllocationPostResponse(BaseModel):
    """Data payload returned when creating an allocation."""

    id: int = Field(description="New allocation ID")


class AllocationGetQuery(BaseModel):
    """Query parameters for retrieving allocations."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset(
        {"pageNumber", "numPerPage", "sortBy", "sortOrder"}
    )

    numPerPage: int = Field(
        default=50,
        description=(
            "Number of followup requests to return per paginated request, when "
            "retrieving a single allocation. Defaults to 50. Can be no larger "
            f"than {MAX_FOLLOWUP_REQUESTS}."
        ),
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    sortBy: Literal["created_at", "modified", "status", "obj"] = Field(
        default="created_at",
        description="The field to sort followup requests by. Defaults to created_at.",
    )
    sortOrder: Literal["asc", "desc"] = Field(
        default="asc",
        description="The sort order, either asc or desc. Defaults to asc.",
    )
    instrument_id: int | None = Field(
        default=None,
        description="Instrument ID to retrieve allocations for.",
    )
    apiType: Literal["api_classname", "api_classname_obsplan"] | None = Field(
        default=None,
        description="Restrict to allocations on instruments with this API class defined.",
    )
    apiImplements: (
        Literal[
            "update",
            "delete",
            "get",
            "submit",
            "send",
            "remove",
            "retrieve",
            "queued",
            "remove_queue",
            "prepare_payload",
            "send_skymap",
            "queued_skymap",
            "remove_skymap",
            "retrieve_log",
            "update_status",
        ]
        | None
    ) = Field(
        default=None,
        description=(
            "Restrict to allocations whose instrument API implements this "
            "method. Requires apiType."
        ),
    )


class AllocationReportGetQuery(BaseModel):
    """Query parameters for the allocation report."""

    model_config = ConfigDict(extra="forbid")

    output_format: Literal["pdf", "png"] = Field(
        default="pdf",
        description="Output format for analysis. Can be png or pdf.",
    )


__all__ = [
    "MAX_OBSERVATION_PLANS",
    "AllocationObservationPlanGetQuery",
    "AllocationPostBody",
    "AllocationPutBody",
    "AllocationPostResponse",
    "AllocationGetQuery",
    "AllocationReportGetQuery",
    "AllocationPost",
    "AllocationUpdate",
    "AllocationDetailResponse",
    "AllocationResponse",
    "AllocationUserResponse",
]


class AllocationDetailResponse(BaseModel):
    """One allocation, with the number of follow-up requests it has.

    ``totalMatches`` counts the requests the allocation has in total; the page
    of them the query asked for is on the allocation itself.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    allocation: AllocationResponse | None = None
    total_matches: int = Field(alias="totalMatches", default=0)
