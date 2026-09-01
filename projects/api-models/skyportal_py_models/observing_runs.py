"""Response models for ``/api/observing_run``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.assignments import AssignmentResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.instruments import InstrumentResponse
from skyportal_py_models.telescopes import EphemerisResponse
from skyportal_py_models.users import UserResponse


class ObservingRunResponse(BaseModel):
    """A classical observing run (``ObservingRun``).

    The list endpoint returns ``to_dict()`` output (columns plus the
    eager-loaded ``instrument``); the single-run endpoint returns a hand-built
    dict that swaps ``created_at``/``modified``/``run_end_utc`` for
    ``ephemeris`` and the run's ``assignments``.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    instrument_id: int | None = None
    calendar_date: date | None = None
    run_end_utc: datetime | None = None
    pi: str | None = None
    observers: str | None = None
    duration: int | None = None
    group_id: int | None = None
    owner_id: int | None = None
    ephemeris: EphemerisResponse | None = None
    instrument: InstrumentResponse | None = None
    group: GroupResponse | None = None
    owner: UserResponse | None = None
    assignments: list[AssignmentResponse] = Field(default_factory=list)
    # typed as dict to avoid an import cycle with sources
    sources: list[dict[str, Any]] = Field(default_factory=list)
