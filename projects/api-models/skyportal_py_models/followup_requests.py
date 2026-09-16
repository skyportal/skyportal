"""Response models for ``/api/followup_request``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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


__all__ = [
    "DefaultFollowupRequestResponse",
    "FacilityTransactionRequestResponse",
    "FacilityTransactionResponse",
    "FollowupRequestResponse",
    "FollowupRequestWatcherResponse",
    "FollowupRequestsPageResponse",
    "PhotometryRequestStatusResponse",
]
