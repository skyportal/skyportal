"""Response models for ``/api/allocation``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import AllocationResponse, AllocationUserResponse

__all__ = [
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
