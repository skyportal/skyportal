"""Response models for ``/api/observing_run``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar

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


class ObservingRunPost(BaseModel):
    """Payload for creating an observing run."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    calendar_date: str
    pi: str | None = None
    observers: str | None = None
    duration: int | None = None
    group_id: int | None = None


class ObservingRunUpdate(BaseModel):
    """Payload for updating an observing run; every field is optional."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: int | None = None
    calendar_date: str | None = None
    pi: str | None = None
    observers: str | None = None
    duration: int | None = None
    group_id: int | None = None


class ObservingRunPostBody(BaseModel):
    """Request body for creating an observing run."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: int = Field(
        description="The ID of the instrument to be used in this run."
    )
    calendar_date: str = Field(
        description="The local calendar date of the run (YYYY-MM-DD)."
    )
    pi: str | None = Field(default=None, description="The PI of the observing run.")
    observers: str | None = Field(
        default=None, description="The names of the observers"
    )
    duration: int | None = Field(
        default=None, description="Number of nights in the observing run"
    )
    group_id: int | None = Field(
        default=None, description="The ID of the group this run is associated with."
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="IDs of the groups that can see this run and its target "
        "list. Defaults to the sitewide group, which is what a run was visible "
        "to before runs became group-scoped.",
    )


class ObservingRunPostResponse(BaseModel):
    """ID of the newly created observing run."""

    id: int = Field(description="New Observing Run ID")


class ObservingRunPutBody(BaseModel):
    """Request body for updating an observing run."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: int | None = Field(
        default=None, description="The ID of the instrument to be used in this run."
    )
    calendar_date: str | None = Field(
        default=None, description="The local calendar date of the run (YYYY-MM-DD)."
    )
    pi: str | None = Field(default=None, description="The PI of the observing run.")
    observers: str | None = Field(
        default=None, description="The names of the observers"
    )
    duration: int | None = Field(
        default=None, description="Number of nights in the observing run"
    )
    group_id: int | None = Field(
        default=None, description="The ID of the group this run is associated with."
    )


class ObservingRunBulkEditBody(BaseModel):
    """Request body for bulk-updating the assignments of an observing run."""

    model_config = ConfigDict(extra="forbid")

    current_status: str | None = Field(
        default=None, description="Assignment status to filter on"
    )
    new_status: str | None = Field(
        default=None, description="New status to apply to the matching assignments"
    )


class ObservingRunGetQuery(BaseModel):
    """Query parameters for listing observing runs."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    upcomingOnly: bool = Field(
        default=False,
        description=(
            "Only return runs that have not finished yet. Callers offering a "
            "run to assign a target to want these, rather than every run ever "
            "scheduled."
        ),
    )
    numPerPage: int | None = Field(
        default=None,
        description="Number of runs to return per paginated request. Defaults to all runs.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
