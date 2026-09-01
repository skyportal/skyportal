"""Response models for ``/api/assignment``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.users import UserResponse


class AssignmentResponse(BaseModel):
    """A target assignment on an observing run (``ClassicalAssignment``)."""

    # ``/api/assignment`` serializes through the auto-generated marshmallow
    # schema, so relationships other than ``obj`` and ``requester`` dump as
    # bare primary keys; ``/api/observing_run/<id>`` instead returns
    # ``to_dict()`` output plus the last-detection and rise/set extras.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    run_id: int | None = None
    requester_id: int | None = None
    last_modified_by_id: int | None = None
    status: str | None = None
    priority: Literal["1", "2", "3", "4", "5"] | None = None
    comment: str | None = None
    # typed as dict to avoid an import cycle with sources
    obj: dict[str, Any] | None = None
    requester: UserResponse | None = None
    last_modified_by: int | None = None
    run: int | None = None
    spectra: list[int] = Field(default_factory=list)
    photometry: list[int] = Field(default_factory=list)
    photometric_series: list[int] = Field(default_factory=list)
    rise_time_utc: str | None = None
    set_time_utc: str | None = None
    accessible_group_names: list[str] = Field(default_factory=list)
    last_detected_mag: float | None = None
    last_detected_filter: str | None = None
    last_detected_mjd: float | None = None
