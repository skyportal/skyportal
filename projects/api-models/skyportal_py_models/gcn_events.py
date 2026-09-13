"""Response models for ``/api/gcn_event``."""

# Rows hanging off a GcnEvent keep their ``gcnevent`` back-reference as a dict:
# GcnEventResponse types the forward direction, so typing the reverse one too
# would make the models mutually recursive.

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import (
    GcnEventCrossmatchStateResponse,
    GcnEventLocalizationResponse,
    GcnEventResponse,
    GcnEventUserResponse,
    GcnNoticeResponse,
    GcnPropertyResponse,
    GcnReportResponse,
    GcnSummaryResponse,
    GcnTriggerResponse,
)
from skyportal_py_models.allocations import AllocationResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.sources import SourceResponse
from skyportal_py_models.users import UserResponse


class GcnCatalogQueryResponse(BaseModel):
    """A catalog query submitted for a GCN event."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    requester_id: int | None = None
    allocation_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    requester: UserResponse | None = None
    allocation: AllocationResponse | None = None
    target_groups: list[GroupResponse] | None = None


class GcnEventsPageResponse(BaseModel):
    """One page of results from a GCN events query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    events: list[GcnEventResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)


# Defined here rather than imported from .gcn, which imports this module.
class GcnEventIdResponse(BaseModel):
    """A response carrying only the ID of the affected GCN event."""

    model_config = ConfigDict(extra="forbid")

    id: int


class GcnEventInstrumentFieldsResponse(BaseModel):
    """Instrument field probabilities for a GCN event localization."""

    model_config = ConfigDict(extra="forbid")

    field_ids: list[int] = Field(default_factory=list)
    probabilities: list[float] = Field(default_factory=list)


class DefaultGcnTagResponse(BaseModel):
    """A rule that automatically tags matching GCN events.

    ``filters`` is free-form JSON; the ingester reads the keys ``gcn_tags``,
    ``notice_types`` and ``localization_tags``.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    requester_id: int | None = None
    default_tag_name: str | None = None
    filters: dict[str, Any] | None = None
    requester: UserResponse | None = None


class GcnEventCrossmatchRequeueResponse(BaseModel):
    """Result of requeueing the alert crossmatch of a GCN event."""

    model_config = ConfigDict(extra="forbid")

    filters_requeued: int


class GcnEventObjResponse(BaseModel):
    """An object's standing against a GCN event."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    dateobs: datetime | None = None
    status: Literal["pending", "confirmed", "ambiguous", "rejected"] | None = None
    confirmer_id: int | None = None
    explanation: str | None = None
    notes: str | None = None
    obj: SourceResponse | None = None
    confirmer: UserResponse | None = None
    # typed as dict: these handlers never load the event
    gcnevent: dict[str, Any] | None = None


class GcnEventTachInfoResponse(BaseModel):
    """The TACH identifiers, aliases and circulars of a GCN event.

    ``circulars`` maps GCN circular ID to that circular's subject line.
    """

    model_config = ConfigDict(extra="forbid")

    tach_id: str | None = None
    aliases: list[str] | None = None
    circulars: dict[str, str] | None = None


__all__ = [
    "DefaultGcnTagResponse",
    "GcnCatalogQueryResponse",
    "GcnEventCrossmatchRequeueResponse",
    "GcnEventCrossmatchStateResponse",
    "GcnEventIdResponse",
    "GcnEventInstrumentFieldsResponse",
    "GcnEventLocalizationResponse",
    "GcnEventObjResponse",
    "GcnEventResponse",
    "GcnEventTachInfoResponse",
    "GcnEventUserResponse",
    "GcnEventsPageResponse",
    "GcnNoticeResponse",
    "GcnPropertyResponse",
    "GcnReportResponse",
    "GcnSummaryResponse",
    "GcnTriggerResponse",
]
