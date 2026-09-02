"""Response models for ``/api/gcn_event``."""

# Rows hanging off a GcnEvent keep their ``gcnevent`` back-reference as a dict:
# GcnEventResponse types the forward direction, so typing the reverse one too
# would make the models mutually recursive.

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

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


MAX_GCNEVENTS = 1000


class GcnEventAliasPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str | None = Field(default=None, description="Alias to add to the event")


class GcnEventAliasDeleteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str | None = Field(
        default=None, description="Alias to remove from the event"
    )


class GcnEventTagPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dateobs: str | None = Field(default=None, description="UTC event timestamp")
    text: str | None = Field(default=None, description="GCN Event tag")


class GcnEventTagPostResponse(BaseModel):
    gcntag_id: int = Field(description="New GcnEvent Tag ID")


class GcnEventTagDeleteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tag: str | None = Field(default=None, description="Tag to remove from the event")


class GcnEventPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    xml: str | None = Field(default=None, description="VOEvent XML content.")
    json_notice: str | dict | None = Field(
        default=None, alias="json", description="JSON notice content."
    )
    dateobs: str | None = Field(default=None, description="UTC event timestamp")
    trigger_id: str | int | None = Field(
        default=None, description="Trigger ID of the event, if any"
    )
    aliases: list[str] | None = Field(default=None, description="Event aliases")
    group_ids: list[int] | None = Field(
        default=None,
        description="Groups the event is readable by. Defaults to the sitewide "
        "public group.",
    )
    tags: list[str] | None = Field(default=None, description="Event tags")
    properties: dict | None = Field(default=None, description="Event properties")
    skymap: dict | str | None = Field(
        default=None,
        description="Localization skymap: a dict (cone/ellipse/polygon/healpix), "
        "a base64/bytes string, or a URL.",
    )


class GcnEventPostResponse(BaseModel):
    gcnevent_id: int | None = Field(description="New GcnEvent ID")
    dateobs: str | None = Field(description="UTC event timestamp of the event")
    notice_id: int | None = Field(description="ID of the created GCN notice, if any")


class GcnEventUserPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    userID: int | None = Field(
        default=None, description="ID of the user to add as advocate"
    )


class GcnSummaryPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, description="Title of the summary")
    number: str | int | None = Field(default=None, description="GCN circular number")
    subject: str | None = Field(default=None, description="Subject of the summary")
    userIds: list[int] | int | None = Field(
        default=None,
        description="User ids to mention in the summary. Comma-separated.",
    )
    groupId: int | None = Field(
        default=None, description="id of the group that creates the summary."
    )
    startDate: str | None = Field(default=None, description="Filter by start date")
    endDate: str | None = Field(default=None, description="Filter by end date")
    localizationName: str | None = Field(
        default=None, description="Name of localization / skymap to use."
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include fields. Defaults to 0.95.",
    )
    numberDetections: int | None = Field(
        default=2,
        description="Return only sources who have at least numberDetections detections. Defaults to 2.",
    )
    numberObservations: int | None = Field(
        default=1,
        description="Return only sources with at least this many observations. Defaults to 1.",
    )
    showSources: bool = Field(default=False, description="Show sources in the summary")
    showGalaxies: bool = Field(
        default=False, description="Show galaxies in the summary"
    )
    showObservations: bool = Field(
        default=False, description="Show observations in the summary"
    )
    noText: bool = Field(
        default=False, description="Do not include text in the summary, only tables."
    )
    photometryInWindow: bool = Field(
        default=False,
        description="Limit photometry to that within startDate and endDate.",
    )
    statsMethod: str = Field(
        default="python",
        description="Method to use for calculating statistics. Defaults to python. Options are python and db.",
    )
    instrumentIds: list[int] | None = Field(
        default=None,
        description="List of instrument ids to include in the summary. Defaults to all instruments if not specified.",
    )
    acknowledgements: str | None = Field(
        default=None, description="Acknowledgements to include in the summary."
    )


class GcnSummaryPostResponse(BaseModel):
    id: int = Field(description="ID of the created GCN summary")


class GcnSummaryPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str | None = Field(default=None, description="Updated summary text")


class GcnReportPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reportName: str | None = Field(default=None, description="Name of the report")
    groupId: int | None = Field(
        default=None, description="id of the group that creates the report."
    )
    startDate: str | None = Field(default=None, description="Filter by start date")
    endDate: str | None = Field(default=None, description="Filter by end date")
    localizationName: str | None = Field(
        default=None, description="Name of localization / skymap to use."
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include fields. Defaults to 0.95.",
    )
    numberDetections: int | None = Field(
        default=2,
        description="Return only sources who have at least numberDetections detections. Defaults to 2.",
    )
    showSources: bool = Field(default=False, description="Show sources in the report")
    showObservations: bool = Field(
        default=False, description="Show observations in the report"
    )
    showSurveyEfficiencies: bool = Field(
        default=False, description="Show survey efficiencies in the report"
    )
    photometryInWindow: bool = Field(
        default=False,
        description="Limit photometry to that within startDate and endDate.",
    )
    statsMethod: str = Field(
        default="python",
        description="Method to use for calculating statistics. Defaults to python. Options are python and db.",
    )
    instrumentIds: list[int] | None = Field(
        default=None,
        description="List of instrument ids to include in the report. Defaults to all instruments if not specified.",
    )


class GcnReportPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict | None = Field(
        default=None, description="Report data (e.g. sources) to update"
    )
    published: bool | None = Field(
        default=None, description="Whether the report is published"
    )


class GcnEventTriggerPutBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    triggered: bool | str | None = Field(
        default=None,
        description="Triggered status of the allocation for this event",
    )


class ObjGcnEventPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). "
        "If provided, filter by GcnEvent.dateobs >= startDate.",
    )
    endDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). "
        "If provided, filter by GcnEvent.dateobs <= endDate.",
    )
    probability: float | None = Field(
        default=None,
        description="Integrated probability contour to crossmatch within (default 0.95).",
    )
    beforeFirstDetection: bool = Field(
        default=False,
        description="If true, only crossmatch GCN events at or before the source's "
        "first detection.",
    )
    gcnTagKeep: list[str] | str | None = Field(
        default=None, description="Only crossmatch events having any of these GCN tags."
    )
    gcnTagRemove: list[str] | str | None = Field(
        default=None, description="Exclude events having any of these GCN tags."
    )
    localizationTagKeep: list[str] | str | None = Field(
        default=None,
        description="Only crossmatch events with a localization having any of these tags.",
    )
    localizationTagRemove: list[str] | str | None = Field(
        default=None,
        description="Exclude events with a localization having any of these tags.",
    )
    gcnPropertiesFilter: list[str] | str | None = Field(
        default=None,
        description='GCN property filters, each "name" or "name:value:op" '
        "(op in lt,le,eq,ne,ge,gt).",
    )
    localizationPropertiesFilter: list[str] | str | None = Field(
        default=None,
        description="Localization property filters, same format as gcnPropertiesFilter.",
    )


class DefaultGcnTagPostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_tag_name: str | None = Field(default=None, description="Default tag name.")
    filters: dict | None = Field(
        default=None,
        description="Filters to determine which of the default gcn tags get executed for which events",
    )


class DefaultGcnTagPostResponse(BaseModel):
    id: int = Field(description="New default gcn tag ID")


class GcnEventAssociationsGetQuery(BaseModel):
    """Query parameters for reading an event's associations."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset(
        {"minConsistency", "maxDays", "includeRejected"}
    )

    minConsistency: float | None = Field(
        default=None,
        description=(
            "Minimum sky-map consistency, 0 to 1. Defaults to your rule for "
            "this pair of messengers."
        ),
    )
    maxDays: float | None = Field(
        default=None,
        description=(
            "Maximum separation in days. Defaults to the configured window for "
            "the detector pair: a neutrino-GW coincidence is judged on seconds, "
            "a GRB-GW one on minutes."
        ),
    )
    includeRejected: bool = Field(
        default=False, description="Include associations already rejected."
    )


class GcnEventGetQuery(BaseModel):
    """Query parameters for retrieving GCN events."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"excludeNoticeContent"})

    startDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by dateobs >= startDate",
    )
    endDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by dateobs <= endDate",
    )
    partialdateobs: str | None = Field(
        default=None,
        description=(
            "Partial dateobs string (or alias substring) to filter events whose "
            "dateobs starts with the given value or whose aliases contain it."
        ),
    )
    gcnTagKeep: list[str] | None = Field(
        default=None,
        description="Comma-separated string of `GcnTag`s. Returns events that match any of them.",
    )
    gcnTagRemove: list[str] | None = Field(
        default=None,
        description="Comma-separated string of `GcnTag`s. Returns events that do not have any of these tags.",
    )
    localizationTagKeep: list[str] | None = Field(
        default=None,
        description="Comma-separated string of `LocalizationTag`s. Returns events that match any of them.",
    )
    localizationTagRemove: list[str] | None = Field(
        default=None,
        description="Comma-separated string of `LocalizationTag`s. Returns events that do not have any of these tags.",
    )
    gcnPropertiesFilter: list[str] | None = Field(
        default=None,
        description=(
            'Comma-separated string of "property: value: operator" single(s) or triplet(s) to filter for events matching '
            'that/those property(ies), i.e. "BNS" or "BNS: 0.5: lt"'
        ),
    )
    localizationPropertiesFilter: list[str] | None = Field(
        default=None,
        description=(
            'Comma-separated string of "property: value: operator" single(s) or triplet(s) to filter for event localizations matching '
            'that/those property(ies), i.e. "area_90" or "area_90: 500: lt"'
        ),
    )
    numPerPage: int = Field(
        default=10,
        description=(
            "Number of GCN events to return per paginated request. "
            f"Defaults to 10. Can be no larger than {MAX_GCNEVENTS}."
        ),
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    sortBy: str | None = Field(
        default=None,
        description='Field to sort by. Currently only "dateobs" is supported.',
    )
    sortOrder: str = Field(
        default="asc",
        description='Sort order, "asc" or "desc". Defaults to "asc".',
    )
    excludeNoticeContent: bool = Field(
        default=False,
        description="If true, do not include the notice content in the response. Defaults to false.",
    )
    # comma-separated: the handler owns the split and its error message
    groupIds: str | None = Field(
        default=None,
        description=(
            "Comma-separated string of group IDs. If provided, only return events "
            "shared with those groups."
        ),
    )
    mmadetectorIds: list[int] | None = Field(
        default=None,
        description=(
            "Comma-separated string of `MMADetector` IDs. Returns events any of "
            "them contributed to."
        ),
    )


class LocalizationGetQuery(BaseModel):
    """Query parameters for retrieving a GCN localization."""

    model_config = ConfigDict(extra="forbid")

    include2DMap: bool = Field(
        default=False,
        description="Boolean indicating whether to include flatted skymap. Defaults to false.",
    )


class GcnReportPostResponse(BaseModel):
    """ID of the created GCN report."""

    id: int = Field(description="ID of the created GCN report")


class LocalizationCrossmatchGetQuery(BaseModel):
    """Query parameters for crossmatching two localizations."""

    model_config = ConfigDict(extra="forbid")

    id1: int = Field(description="ID of the first localization.")
    id2: int = Field(description="ID of the second localization.")


class GcnEventInstrumentFieldGetQuery(BaseModel):
    """Query parameters for instrument field probabilities for a skymap."""

    model_config = ConfigDict(extra="forbid")

    localization_name: str | None = Field(
        default=None, description="Localization map name"
    )
    integrated_probability: float = Field(
        default=0.95, description="Cumulative integrated probability threshold"
    )


class GcnAssociationRuleBody(BaseModel):
    """One group's cut for a pair of messengers."""

    model_config = ConfigDict(extra="forbid")

    group_id: int = Field(description="ID of the group the rule belongs to.")

    detector_type_1: str = Field(
        description=f"One of {', '.join(('gravitational-wave', 'neutrino', 'gamma-ray-burst', 'x-ray'))}.",
    )
    detector_type_2: str = Field(
        description=f"One of {', '.join(('gravitational-wave', 'neutrino', 'gamma-ray-burst', 'x-ray'))}.",
    )
    tags_1: list[str] = Field(
        default_factory=list,
        description="Tags the first messenger's event must carry at least one "
        "of (e.g. BNS, NSBH). Empty means no restriction.",
    )
    tags_2: list[str] = Field(
        default_factory=list,
        description="Tags the second messenger's event must carry at least one "
        "of. Empty means no restriction.",
    )
    days: float = Field(
        description="Widest separation in days for this pair to be coincident."
    )
    min_consistency: float = Field(
        default=0.5,
        description="Smallest sky-map consistency, 0 to 1: how well the two "
        "localizations must agree, as a fraction of the most they could.",
    )


class GcnEventObjPostBody(BaseModel):
    """Request body for confirming or rejecting a source in a GCN."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(
        description="The source_id of the source to confirm or reject"
    )
    localization_name: str = Field(
        description="The name of the localization of the event"
    )
    localization_cumprob: float = Field(
        description="The cumprob of the localization of the event"
    )
    status: Literal["pending", "confirmed", "ambiguous", "rejected"] = Field(
        description="Standing of the source against the event"
    )
    start_date: str = Field(
        description="Choose sources with a first detection after start_date, "
        "as an arrow parseable string"
    )
    end_date: str = Field(
        description="Choose sources with a last detection before end_date, "
        "as an arrow parseable string"
    )
    explanation: str | None = Field(
        default=None, description="Explanation of the confirmation/rejection"
    )
    notes: str | None = Field(
        default=None, description="Notes about the confirmation/rejection"
    )


class GcnEventObjPatchBody(BaseModel):
    """Request body for updating the confirmed/rejected status of a source in
    a GCN."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["pending", "confirmed", "ambiguous", "rejected"] = Field(
        description="Standing of the source against the event"
    )
    explanation: str | None = Field(
        default=None, description="Explanation of the confirmation/rejection"
    )
    notes: str | None = Field(
        default=None, description="Notes about the confirmation/rejection"
    )


class GcnEventObjIdResponse(BaseModel):
    """ID of the affected gcn_event_obj row."""

    id: int = Field(description="The id of the gcn_event_obj")


class SourcesConfirmedInGCNGetQuery(BaseModel):
    """Query parameters for retrieving sources confirmed/rejected in a GCN."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    sourcesIDList: str = Field(
        default="",
        description="A comma-separated list of source_id's to retrieve. "
        "If not provided, all sources confirmed or rejected in GCN will be returned.",
    )


__all__ = [
    "MAX_GCNEVENTS",
    "GcnEventAliasPostBody",
    "GcnEventAliasDeleteBody",
    "GcnEventTagPostBody",
    "GcnEventTagPostResponse",
    "GcnEventTagDeleteBody",
    "GcnEventPostBody",
    "GcnEventPostResponse",
    "GcnEventUserPostBody",
    "GcnSummaryPostBody",
    "GcnSummaryPostResponse",
    "GcnSummaryPatchBody",
    "GcnReportPostBody",
    "GcnReportPatchBody",
    "GcnEventTriggerPutBody",
    "ObjGcnEventPostBody",
    "DefaultGcnTagPostBody",
    "DefaultGcnTagPostResponse",
    "GcnEventAssociationsGetQuery",
    "GcnEventGetQuery",
    "LocalizationGetQuery",
    "GcnReportPostResponse",
    "LocalizationCrossmatchGetQuery",
    "GcnEventInstrumentFieldGetQuery",
    "GcnAssociationRuleBody",
    "GcnEventObjPostBody",
    "GcnEventObjPatchBody",
    "GcnEventObjIdResponse",
    "SourcesConfirmedInGCNGetQuery",
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
