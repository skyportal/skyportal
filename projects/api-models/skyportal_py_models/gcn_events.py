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


class GcnEventPost(BaseModel):
    """Payload for ingesting a GCN event."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    xml: str | None = None
    json_notice: dict[str, Any] | None = Field(default=None, alias="json")
    dateobs: str | None = None
    trigger_id: str | None = None
    aliases: list[str] | None = None
    group_ids: list[int] | None = None
    properties: dict[str, Any] | None = None
    tags: list[str] | None = None
    skymap: Any = None


class GcnSummaryPost(BaseModel):
    """Payload for generating a GCN event summary."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    title: str
    group_id: int = Field(alias="groupId")
    number: int | None = None
    subject: str | None = None
    user_ids: list[int] | None = Field(default=None, alias="userIds")
    start_date: str | None = Field(default=None, alias="startDate")
    end_date: str | None = Field(default=None, alias="endDate")
    localization_name: str | None = Field(default=None, alias="localizationName")
    localization_cumprob: float | None = Field(
        default=None, alias="localizationCumprob"
    )
    number_detections: int | None = Field(default=None, alias="numberDetections")
    number_observations: int | None = Field(default=None, alias="numberObservations")
    show_sources: bool | None = Field(default=None, alias="showSources")
    show_galaxies: bool | None = Field(default=None, alias="showGalaxies")
    show_observations: bool | None = Field(default=None, alias="showObservations")
    no_text: bool | None = Field(default=None, alias="noText")
    photometry_in_window: bool | None = Field(default=None, alias="photometryInWindow")
    stats_method: str | None = Field(default=None, alias="statsMethod")
    instrument_ids: list[int] | None = Field(default=None, alias="instrumentIds")
    acknowledgements: str | None = None


class GcnReportPost(BaseModel):
    """Payload for generating a GCN event report."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    report_name: str = Field(alias="reportName")
    group_id: int = Field(alias="groupId")
    start_date: str | None = Field(default=None, alias="startDate")
    end_date: str | None = Field(default=None, alias="endDate")
    localization_name: str | None = Field(default=None, alias="localizationName")
    localization_cumprob: float | None = Field(
        default=None, alias="localizationCumprob"
    )
    number_detections: int | None = Field(default=None, alias="numberDetections")
    show_sources: bool | None = Field(default=None, alias="showSources")
    show_observations: bool | None = Field(default=None, alias="showObservations")
    show_survey_efficiencies: bool | None = Field(
        default=None, alias="showSurveyEfficiencies"
    )
    photometry_in_window: bool | None = Field(default=None, alias="photometryInWindow")
    stats_method: str | None = Field(default=None, alias="statsMethod")
    instrument_ids: list[int] | None = Field(default=None, alias="instrumentIds")


class DefaultGcnTagPost(BaseModel):
    """Payload for creating a default GCN tag."""

    model_config = ConfigDict(extra="forbid")

    default_tag_name: str
    filters: dict[str, Any] | None = None


class GcnEventObjPost(BaseModel):
    """Payload for recording an object's standing against a GCN event."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    status: Literal["pending", "confirmed", "ambiguous", "rejected"]
    localization_name: str
    localization_cumprob: float
    start_date: str
    end_date: str
    explanation: str | None = None
    notes: str | None = None


class GcnEventObjCrossmatchPost(BaseModel):
    """Payload for crossmatching an object against GCN events."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    probability: float | None = None
    before_first_detection: bool | None = Field(
        default=None, alias="beforeFirstDetection"
    )
    gcn_tag_keep: list[str] | None = Field(default=None, alias="gcnTagKeep")
    gcn_tag_remove: list[str] | None = Field(default=None, alias="gcnTagRemove")
    localization_tag_keep: list[str] | None = Field(
        default=None, alias="localizationTagKeep"
    )
    localization_tag_remove: list[str] | None = Field(
        default=None, alias="localizationTagRemove"
    )
    gcn_properties_filter: list[str] | None = Field(
        default=None, alias="gcnPropertiesFilter"
    )
    localization_properties_filter: list[str] | None = Field(
        default=None, alias="localizationPropertiesFilter"
    )


__all__ = [
    "GcnEventPost",
    "GcnSummaryPost",
    "GcnReportPost",
    "DefaultGcnTagPost",
    "GcnEventObjPost",
    "GcnEventObjCrossmatchPost",
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
