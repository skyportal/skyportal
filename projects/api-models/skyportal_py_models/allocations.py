"""Response models for ``/api/allocation``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import AllocationResponse, AllocationUserResponse


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


__all__ = [
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
