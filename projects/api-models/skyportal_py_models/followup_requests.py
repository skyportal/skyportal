"""Response models for ``/api/followup_request``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import (
    FacilityTransactionRequestResponse,
    FacilityTransactionResponse,
)
from skyportal_py_models.allocations import AllocationResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.users import UserResponse


class FollowupRequestWatcherResponse(BaseModel):
    """A user watching a follow-up request (``FollowupRequestUser``)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    followuprequest_id: int | None = None
    user_id: int | None = None


class FollowupRequestResponse(BaseModel):
    """A follow-up observation request (``FollowupRequest``)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    allocation_id: int | None = None
    requester_id: int | None = None
    last_modified_by_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    comment: str | None = None
    # typed as dict to avoid an import cycle with sources
    obj: dict[str, Any] | None = None
    allocation: AllocationResponse | None = None
    requester: UserResponse | None = None
    last_modified_by: UserResponse | None = None
    target_groups: list[GroupResponse] = Field(default_factory=list)
    watchers: list[FollowupRequestWatcherResponse] = Field(default_factory=list)
    transactions: list[FacilityTransactionResponse] = Field(default_factory=list)
    transaction_requests: list[FacilityTransactionRequestResponse] = Field(
        default_factory=list
    )
    # results pointing back at the requesting object: these are the raw
    # relationship rows, whose shape is not modelled here
    photometry: list[dict[str, Any]] = Field(default_factory=list)
    photometric_series: list[dict[str, Any]] = Field(default_factory=list)
    spectra: list[dict[str, Any]] = Field(default_factory=list)
    rise_time_utc: str | None = None
    set_time_utc: str | None = None


class FollowupRequestsPageResponse(BaseModel):
    """One page of results from a follow-up requests query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    followup_requests: list[FollowupRequestResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)


class DefaultFollowupRequestResponse(BaseModel):
    """A default follow-up request (``DefaultFollowupRequest``)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    requester_id: int | None = None
    allocation_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    default_followup_name: str | None = None
    source_filter: dict[str, Any] | str | None = None
    constraints: dict[str, Any] | None = None
    priority_order: str | None = None
    validity_days: int | None = None
    comment: str | None = None
    implements_update: bool | None = None
    allocation: AllocationResponse | None = None
    requester: UserResponse | None = None
    target_groups: list[GroupResponse] = Field(default_factory=list)


class PhotometryRequestStatusResponse(BaseModel):
    """Status of a follow-up request after a photometry retrieval."""

    model_config = ConfigDict(extra="forbid")

    id: int
    request_status: str | None = None


class FollowupRequestPost(BaseModel):
    """Payload for submitting a follow-up request."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    allocation_id: int
    payload: dict[str, Any]
    target_group_ids: list[int] | None = None


class DefaultFollowupRequestPost(BaseModel):
    """Payload for creating a default follow-up request."""

    model_config = ConfigDict(extra="forbid")

    allocation_id: int
    payload: dict[str, Any]
    default_followup_name: str
    source_filter: dict[str, Any]
    target_group_ids: list[int] | None = None
    comment: str | None = None
    implements_update: bool | None = None
    priority_order: str | None = None
    validity_days: int | None = None
    radius: float | None = None
    not_if_duplicates: bool | None = None
    source_group_ids: list[int] | None = None
    ignore_source_group_ids: list[int] | None = None
    not_if_classified: bool | None = None
    not_if_spectra_exist: bool | None = None
    not_if_tns_classified: bool | None = None
    not_if_tns_reported: float | None = None
    not_if_assignment_exists: bool | None = None
    ignore_allocation_ids: list[int] | None = None


MAX_FOLLOWUP_REQUESTS = 1000


class AssignmentPostBody(BaseModel):
    """Request body for posting a new observing-run assignment."""

    model_config = ConfigDict(extra="forbid")

    run_id: int = Field(description="ID of the observing run to assign the target to.")
    obj_id: str = Field(description="The ID of the object to observe.")
    priority: str = Field(
        description="Priority of the request, (lowest = 1, highest = 5)."
    )
    status: str | None = Field(default=None, description="The status of the request.")
    comment: str | None = Field(
        default=None, description="An optional comment describing the request."
    )


class AssignmentPostResponse(BaseModel):
    """Data payload returned when posting a new assignment."""

    id: int = Field(description="New assignment ID")


class AssignmentPutBody(BaseModel):
    """Request body for updating an observing-run assignment."""

    model_config = ConfigDict(extra="forbid")

    run_id: int | None = Field(default=None, description="ID of the observing run.")
    obj_id: str | None = Field(
        default=None, description="The ID of the object to observe."
    )
    priority: str | None = Field(
        default=None,
        description="Priority of the request, (lowest = 1, highest = 5).",
    )
    status: str | None = Field(default=None, description="The status of the request.")
    comment: str | None = Field(
        default=None, description="An optional comment describing the request."
    )


class FollowupRequestGetQuery(BaseModel):
    """Query parameters for retrieving followup requests."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"includeObjThumbnails"})

    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "created_at >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "created_at <= endDate"
        ),
    )
    observationStartDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "payload.start_date >= observationStartDate"
        ),
    )
    observationEndDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "payload.end_date <= observationEndDate"
        ),
    )
    sourceID: str | None = Field(
        default=None,
        description="Portion of ID to filter on",
    )
    instrumentID: int | None = Field(
        default=None,
        description="Instrument ID to filter on",
    )
    allocationID: int | None = Field(
        default=None,
        description="Allocation ID to filter on",
    )
    requesters: list[int] = Field(
        default_factory=list,
        description="Comma-separated list of user IDs to filter requests by requester",
    )
    priorityThreshold: float | None = Field(
        default=None,
        description=(
            "Threshold on request priority to include. If provided, filter by "
            "payload.priority >= priorityThreshold"
        ),
    )
    status: str | None = Field(
        default=None,
        description="String to match status of request against",
    )
    includeObjThumbnails: bool = Field(
        default=True,
        description="Boolean indicating whether to include associated thumbnails. Defaults to True.",
    )
    sortBy: Literal["created_at", "modified", "status", "obj"] = Field(
        default="created_at",
        description="Field to sort by. Defaults to created_at.",
    )
    sortOrder: Literal["asc", "desc"] = Field(
        default="asc",
        description="Sort order. Defaults to asc.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=100,
        description=(
            "Number of followup requests to return per paginated request. "
            f"Defaults to 100. Max {MAX_FOLLOWUP_REQUESTS}."
        ),
    )


class FollowupRequestPostBody(BaseModel):
    """Request body for submitting a new follow-up request."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str = Field(description="ID of the target Obj.")
    payload: dict[str, Any] | None = Field(
        default=None, description="Content of the followup request."
    )
    status: str | None = Field(default=None, description="The status of the request.")
    allocation_id: int = Field(description="Followup request allocation ID.")
    target_group_ids: list[int] | None = Field(
        default=None,
        description="IDs of groups to share the results of the followup request with.",
    )
    not_if_duplicates: bool | None = Field(
        default=None,
        description="If true, the followup request will not be executed if the object already has a pending or completed request of the same allocation.",
    )
    source_group_ids: list[int] | None = Field(
        default=None,
        description="IDs of groups to which there must be a source for the object associated with the followup request.",
    )
    not_if_classified: bool | None = Field(
        default=None,
        description="If true, the followup request will not be executed if there are any sources within radius with (human-only) classifications.",
    )
    not_if_spectra_exist: bool | None = Field(
        default=None,
        description="If true, the followup request will not be executed if there are any sources within radius that have spectra.",
    )
    not_if_tns_classified: bool | None = Field(
        default=None,
        description="If true, the followup request will not be executed if any object within radius is already classified as SN in TNS.",
    )
    not_if_tns_reported: float | None = Field(
        default=None,
        description="If there are any sources within radius with TNS reports, and the source has been discovered within before this many hours from the current time, the followup request will not be executed.",
    )
    not_if_assignment_exists: bool | None = Field(
        default=None,
        description="If there are any sources within radius that are assigned to an observing run, the followup request will not be executed.",
    )
    ignore_source_group_ids: list[int] | None = Field(
        default=None,
        description="If there are any sources within radius saved to any of these groups, the followup request will not be executed.",
    )
    radius: float | None = Field(
        default=None, description="Radius of to use when checking constraints."
    )
    ignore_allocation_ids: list[int] | None = Field(
        default=None,
        description="If there are any existing requests from the allocations that are pending or completed, the followup request will not be executed.",
    )
    refreshSource: bool = Field(
        default=True,
        description="Whether to refresh the source page after posting the request.",
    )
    refreshRequests: bool = Field(
        default=False,
        description="Whether to refresh the follow-up requests list after posting the request.",
    )


class FollowupRequestPostResponse(BaseModel):
    """Data payload returned when posting a follow-up request."""

    id: int | None = Field(
        description="New follow-up request ID, null when the request was ignored"
    )
    request_status: str | None = Field(
        default=None, description="Status of the new follow-up request"
    )
    ignored: bool | None = Field(
        default=None,
        description="True when constraints prevented the request from being sent",
    )
    message: str | None = Field(default=None, description="Why the request was ignored")


class FollowupRequestPutBody(BaseModel):
    """Request body for updating a follow-up request.

    Every field is optional: a body containing ``status`` performs a
    status-only update, otherwise the request is (re)submitted/updated and the
    marshmallow ``FollowupRequestPost`` schema enforces the required fields.
    """

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(default=None, description="ID of the target Obj.")
    payload: dict[str, Any] | None = Field(
        default=None, description="Content of the followup request."
    )
    status: str | None = Field(default=None, description="The status of the request.")
    allocation_id: int | None = Field(
        default=None, description="Followup request allocation ID."
    )
    target_group_ids: list[int] | None = Field(
        default=None,
        description="IDs of groups to share the results of the followup request with.",
    )
    not_if_duplicates: bool | None = Field(
        default=None,
        description="If true, the followup request will not be executed if the object already has a pending or completed request of the same allocation.",
    )
    source_group_ids: list[int] | None = Field(
        default=None,
        description="IDs of groups to which there must be a source for the object associated with the followup request.",
    )
    not_if_classified: bool | None = Field(
        default=None,
        description="If true, the followup request will not be executed if there are any sources within radius with (human-only) classifications.",
    )
    not_if_spectra_exist: bool | None = Field(
        default=None,
        description="If true, the followup request will not be executed if there are any sources within radius that have spectra.",
    )
    not_if_tns_classified: bool | None = Field(
        default=None,
        description="If true, the followup request will not be executed if any object within radius is already classified as SN in TNS.",
    )
    not_if_tns_reported: float | None = Field(
        default=None,
        description="If there are any sources within radius with TNS reports, and the source has been discovered within before this many hours from the current time, the followup request will not be executed.",
    )
    not_if_assignment_exists: bool | None = Field(
        default=None,
        description="If there are any sources within radius that are assigned to an observing run, the followup request will not be executed.",
    )
    ignore_source_group_ids: list[int] | None = Field(
        default=None,
        description="If there are any sources within radius saved to any of these groups, the followup request will not be executed.",
    )
    radius: float | None = Field(
        default=None, description="Radius of to use when checking constraints."
    )
    ignore_allocation_ids: list[int] | None = Field(
        default=None,
        description="If there are any existing requests from the allocations that are pending or completed, the followup request will not be executed.",
    )
    refreshSource: bool = Field(
        default=True,
        description="Whether to refresh the source page after updating the request.",
    )
    refreshRequests: bool = Field(
        default=False,
        description="Whether to refresh the follow-up requests list after updating the request.",
    )


class FollowupRequestDeleteBody(BaseModel):
    """Request body for deleting a follow-up request."""

    model_config = ConfigDict(extra="forbid")

    refreshSource: bool = Field(
        default=True,
        description="Whether to refresh the source page after deleting the request.",
    )
    refreshRequests: bool = Field(
        default=False,
        description="Whether to refresh the follow-up requests list after deleting the request.",
    )


class FollowupRequestCommentPutBody(BaseModel):
    """Request body for updating a follow-up request comment."""

    model_config = ConfigDict(extra="forbid")

    comment: str | None = Field(
        default=None, description="Comment to add to the follow-up request"
    )


class FollowupRequestCommentPutResponse(BaseModel):
    """Data payload returned when updating a follow-up request comment."""

    id: int = Field(description="ID of the updated follow-up request")


class FollowupRequestSchedulerGetQuery(BaseModel):
    """Query parameters for retrieving a followup requests schedule."""

    model_config = ConfigDict(extra="forbid")

    sourceID: str | None = Field(
        default=None,
        description="Portion of ID to filter on",
    )
    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "created_at >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by "
            "created_at <= endDate"
        ),
    )
    status: str | None = Field(
        default=None,
        description="String to match status of request against",
    )
    priorityThreshold: float | None = Field(
        default=None,
        description=(
            "Threshold on request priority to include. If provided, filter by "
            "payload.priority >= priorityThreshold"
        ),
    )
    timeResolution: float = Field(
        default=20,
        description="Time resolution for scheduler creation in seconds. Defaults to 20.",
    )
    observationStartDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, start time "
            "of observation window, otherwise now."
        ),
    )
    observationEndDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, end time "
            "of observation window, otherwise 12 hours from now."
        ),
    )
    includeStandards: bool = Field(
        default=False,
        description="Include standards in schedule. Defaults to False.",
    )
    standardsOnly: bool = Field(
        default=False,
        description="Only request standards in schedule. Defaults to False.",
    )
    standardType: str = Field(
        default="ESO",
        description="Origin of the standard stars, defined in config.yaml. Defaults to ESO.",
    )
    magnitudeRange: str | None = Field(
        default=None,
        description='lowest and highest magnitude to return, e.g. "(12,9)"',
    )
    output_format: str = Field(
        default="csv",
        description="Output format for schedule. Can be png, pdf, or csv",
    )


class FollowupRequestPrioritizationPutBody(BaseModel):
    """Request body for reprioritizing follow-up requests."""

    model_config = ConfigDict(extra="forbid")

    requestIds: list[int] | None = Field(
        default=None, description="List of follow-up request IDs"
    )
    priorityType: str = Field(
        default="magnitude",
        description="Priority source. Must be either localization or magnitude. Defaults to magnitude.",
    )
    magnitudeOrdering: str = Field(
        default="ascending",
        description="Ordering for brightness based prioritization. Must be either ascending (brightest first) or descending (faintest first). Defaults to ascending.",
    )
    localizationId: int | None = Field(
        default=None, description="Filter by localization ID"
    )
    minimumPriority: float = Field(
        default=1, description="Minimum priority for the instrument. Defaults to 1."
    )
    maximumPriority: float = Field(
        default=5, description="Maximum priority for the instrument. Defaults to 5."
    )


class DefaultFollowupRequestPostBody(BaseModel):
    """Request body for creating a default follow-up request."""

    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any] = Field(
        description="Content of the default follow-up request."
    )
    allocation_id: int = Field(description="Follow-up request allocation ID.")
    target_group_ids: list[int] | None = Field(
        default=None,
        description="IDs of groups to share the results of the default follow-up request with.",
    )
    default_followup_name: str = Field(
        description="Unique name of the default follow-up request."
    )
    source_filter: dict[str, Any] | str = Field(
        description="Source filter used to decide which saved sources this default "
        "follow-up request applies to (keys: name, group_id, origin, classification).",
    )
    not_if_duplicates: bool | None = Field(
        default=None,
        description="If true, the request will not be submitted if the object already has a pending or completed request of the same allocation.",
    )
    source_group_ids: list[int] | None = Field(
        default=None,
        description="IDs of groups to which there must be a source for the object for the request to be submitted.",
    )
    ignore_source_group_ids: list[int] | None = Field(
        default=None,
        description="If there are any sources within radius saved to any of these groups, the request will not be submitted.",
    )
    not_if_classified: bool | None = Field(
        default=None,
        description="If true, the request will not be submitted if there are any sources within radius with (human-only) classifications.",
    )
    not_if_spectra_exist: bool | None = Field(
        default=None,
        description="If true, the request will not be submitted if there are any sources within radius that have spectra.",
    )
    not_if_tns_classified: bool | None = Field(
        default=None,
        description="If true, the request will not be submitted if any object within radius is already classified as SN in TNS.",
    )
    not_if_tns_reported: float | None = Field(
        default=None,
        description="If there are any sources within radius with TNS reports discovered more than this many hours ago, the request will not be submitted.",
    )
    not_if_assignment_exists: bool | None = Field(
        default=None,
        description="If there are any sources within radius that are assigned to an observing run, the request will not be submitted.",
    )
    ignore_allocation_ids: list[int] | None = Field(
        default=None,
        description="If there are any existing pending or completed requests from these allocations within radius, the request will not be submitted.",
    )
    radius: float | None = Field(
        default=None,
        description="Radius (arcsec) to use when checking constraints.",
    )
    priority_order: str | None = Field(
        default=None,
        description="Whether higher priority values mean higher ('asc', default) or "
        "lower ('desc') observing priority. Controls whether an incoming "
        "auto-trigger bumps an existing request's priority.",
    )
    validity_days: int | None = Field(
        default=None,
        description="Number of days an auto-submitted request stays valid (end_date = "
        "start_date + validity_days). Defaults to 7. Ignored for "
        "urgency-based instruments.",
    )
    comment: str | None = Field(
        default=None,
        description="Optional comment posted to the source when a follow-up request is "
        "auto-submitted from this default request.",
    )
    implements_update: bool | None = Field(
        default=None,
        description="Operator override: if false, never priority-bump an existing "
        "matching request even if the instrument supports updates. Defaults to true.",
    )


class DefaultFollowupRequestPostResponse(BaseModel):
    """Data payload returned when creating a default follow-up request."""

    id: int = Field(description="New default follow-up request ID")


class FollowupRequestWatcherPostBody(BaseModel):
    """Request body for adding a follow-up request to the watch list."""

    model_config = ConfigDict(extra="forbid")

    refreshSource: bool = Field(
        default=True,
        description="Whether to refresh the source page after watching the request.",
    )
    refreshRequests: bool = Field(
        default=False,
        description="Whether to refresh the follow-up requests list after watching the request.",
    )


class FollowupRequestWatcherDeleteBody(BaseModel):
    """Request body for removing a follow-up request from the watch list."""

    model_config = ConfigDict(extra="forbid")

    refreshSource: bool = Field(
        default=True,
        description="Whether to refresh the source page after unwatching the request.",
    )
    refreshRequests: bool = Field(
        default=False,
        description="Whether to refresh the follow-up requests list after unwatching the request.",
    )


class PhotometryRequestGetQuery(BaseModel):
    """Query parameters for retrieving a photometry request."""

    model_config = ConfigDict(extra="forbid")

    refreshSource: bool = Field(
        default=True,
        description="Whether to refresh the source page once the request is retrieved. Defaults to true.",
    )
    refreshRequests: bool = Field(
        default=False,
        description="Whether to refresh the follow-up request lists once the request is retrieved. Defaults to false.",
    )


__all__ = [
    "MAX_FOLLOWUP_REQUESTS",
    "AssignmentPostBody",
    "AssignmentPostResponse",
    "AssignmentPutBody",
    "FollowupRequestGetQuery",
    "FollowupRequestPostBody",
    "FollowupRequestPostResponse",
    "FollowupRequestPutBody",
    "FollowupRequestDeleteBody",
    "FollowupRequestCommentPutBody",
    "FollowupRequestCommentPutResponse",
    "FollowupRequestSchedulerGetQuery",
    "FollowupRequestPrioritizationPutBody",
    "DefaultFollowupRequestPostBody",
    "DefaultFollowupRequestPostResponse",
    "FollowupRequestWatcherPostBody",
    "FollowupRequestWatcherDeleteBody",
    "PhotometryRequestGetQuery",
    "FollowupRequestPost",
    "DefaultFollowupRequestPost",
    "DefaultFollowupRequestResponse",
    "FacilityTransactionRequestResponse",
    "FacilityTransactionResponse",
    "FollowupRequestResponse",
    "FollowupRequestWatcherResponse",
    "FollowupRequestsPageResponse",
    "PhotometryRequestStatusResponse",
]
