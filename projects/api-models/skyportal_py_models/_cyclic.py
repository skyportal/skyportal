"""Models whose references cross module boundaries in both directions.

These would be an import cycle if each lived in its own resource module, so
they are defined together here and re-exported from those modules: import
them from the resource module, not from this one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.filters import FilterResponse
from skyportal_py_models.mmadetectors import MMADetectorResponse
from skyportal_py_models.streams import StreamResponse


class GroupMemberResponse(BaseModel):
    """A group member as assembled by the ``GET /api/groups/{id}`` handler."""

    # The handler hand-builds this dict from a ``GroupUser`` and its ``User``
    # rather than serializing either model.

    model_config = ConfigDict(extra="forbid")

    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    oauth_uid: str | None = None
    admin: bool | None = None
    can_save: bool | None = None
    can_share_photometry: bool | None = None


class GroupUserResponse(BaseModel):
    """A user's membership of a group (the ``GroupUser`` join model)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    group_id: int | None = None
    user_id: int | None = None
    admin: bool | None = None
    can_save: bool | None = None
    can_share_photometry: bool | None = None
    user: UserResponse | None = None
    group: GroupResponse | None = None


class GroupResponse(BaseModel):
    """A SkyPortal group."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str
    nickname: str | None = None
    description: str | None = None
    private: bool | None = None
    auto_accept_requests: bool | None = None
    discoverable_data: bool | None = None
    single_user_group: bool = False
    streams: list[StreamResponse] | None = None
    filters: list[FilterResponse] | None = None
    group_users: list[GroupUserResponse] | None = None
    users: list[GroupMemberResponse] | None = None


class UserResponse(BaseModel):
    """A SkyPortal user (baselayer ``User``)."""

    # ``User.to_dict`` returns the table columns only, minus ``preferences``;
    # ``roles``/``acls``/``permissions``/``gravatar_url`` and, for system
    # admins, ``groups``/``streams`` are injected by the handler. Requesters
    # without access to the full record get the reduced ``public_user_info``
    # shape instead.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    username: str
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    affiliations: list[str] = Field(default_factory=list)
    contact_email: str | None = None
    contact_phone: str | None = None
    oauth_uid: str | None = None
    is_bot: bool | None = None
    expiration_date: datetime | None = None
    permissions: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    acls: list[str] = Field(default_factory=list)
    gravatar_url: str | None = None
    # group names in the public-profile shape, full groups otherwise
    groups: list[GroupResponse] | list[str] | None = None
    streams: list[StreamResponse] | None = None


class AllocationUserResponse(BaseModel):
    """A join row mapping a user to an allocation.

    ``allocation`` stays untyped to avoid a recursive model.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    allocation_id: int | None = None
    user_id: int | None = None
    user: UserResponse | None = None
    allocation: dict[str, Any] | None = None


class EphemerisResponse(BaseModel):
    """Sun/twilight times computed for a telescope's site.

    Every value is None when the telescope has no usable observer (no fixed
    location, or missing coordinates), in which case an empty object is sent.
    """

    model_config = ConfigDict(extra="forbid")

    sunset_utc: str | None = None
    sunrise_utc: str | None = None
    twilight_morning_astronomical_utc: str | None = None
    twilight_evening_astronomical_utc: str | None = None
    twilight_morning_nautical_utc: str | None = None
    twilight_evening_nautical_utc: str | None = None
    utc_offset_hours: float | None = None
    sunset_unix_ms: float | None = None
    sunrise_unix_ms: float | None = None
    twilight_morning_astronomical_unix_ms: float | None = None
    twilight_evening_astronomical_unix_ms: float | None = None
    twilight_morning_nautical_unix_ms: float | None = None
    twilight_evening_nautical_unix_ms: float | None = None


class InstrumentFieldResponse(BaseModel):
    """One field (pointing) of an instrument.

    ``contour`` and ``contour_summary`` are deferred and only present when the
    request asked for GeoJSON. ``airmass`` is injected when the fields are
    sliced by a localization.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    instrument_id: int | None = None
    field_id: int | None = None
    ra: float | None = None
    dec: float | None = None
    contour: dict[str, Any] | None = None
    contour_summary: dict[str, Any] | None = None
    reference_filters: list[str] | None = None
    reference_filter_mags: list[float] | None = None
    tiles: list[dict[str, Any]] | None = None
    airmass: float | None = None


class TelescopeResponse(BaseModel):
    """A telescope, as returned by the telescope endpoints."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str
    nickname: str | None = None
    lat: float | None = None
    lon: float | None = None
    elevation: float | None = None
    mpc_obscode: str | None = None
    diameter: float | None = None
    skycam_link: str | None = None
    weather_link: str | None = None
    robotic: bool | None = None
    fixed_location: bool | None = None
    acknowledgment: str | None = None
    instruments: list[InstrumentResponse] | None = None
    allocations: list[AllocationResponse] | None = None
    is_night_astronomical: bool | None = None
    morning: str | bool | None = None
    evening: str | bool | None = None


class InstrumentResponse(BaseModel):
    """An instrument, as returned by the instrument endpoints.

    ``log_exists``, ``number_of_fields`` and ``region_summary`` are injected
    by the instrument endpoints rather than being columns.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    type: Literal["imager", "spectrograph", "imaging spectrograph"] | None = None
    band: str | None = None
    acknowledgment: str | None = None
    telescope_id: int | None = None
    telescope: TelescopeResponse | None = None
    filters: list[str] = Field(default_factory=list)
    sensitivity_data: dict[str, Any] | None = None
    configuration_data: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
    last_status_update: datetime | None = None
    api_classname: str | None = None
    api_classname_obsplan: str | None = None
    listener_classname: str | None = None
    treasuremap_id: int | None = None
    tns_id: int | None = None
    across_id: str | None = None
    region: str | None = None
    has_fields: bool | None = None
    has_region: bool | None = None
    fields: list[InstrumentFieldResponse] | None = None
    allocations: list[AllocationResponse] | None = None
    log_exists: bool | None = None
    number_of_fields: int | None = None
    region_summary: str | None = None


class AllocationResponse(BaseModel):
    """An observing-time allocation on an instrument.

    ``allocation_users`` is a list of plain users on the allocation endpoints
    (the handlers substitute ``allocation_user.user``) but a list of join rows
    when it arrives nested inside a telescope payload, so both are accepted.
    ``requests``, ``default_requests``, ``default_observation_plans``,
    ``catalog_queries``, ``observation_plans``, ``gcn_triggers`` and ``group``
    stay untyped: those models point back at ``Allocation``, so typing them
    would risk an import cycle. ``requests``, ``ephemeris`` and ``telescope``
    are injected by the single-allocation endpoint. The encrypted ``_altdata``
    column is never serialized.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    pi: str | None = None
    proposal_id: str | None = None
    hours_allocated: float | None = None
    validity_ranges: list[dict[str, Any]] | None = None
    default_share_group_ids: list[int] | None = None
    types: (
        list[Literal["triggered", "forced_photometry", "observation_plan"]] | None
    ) = None
    group_id: int
    instrument_id: int
    instrument: InstrumentResponse | None = None
    allocation_users: list[UserResponse | AllocationUserResponse] | None = None
    group: dict[str, Any] | None = None
    requests: list[dict[str, Any]] | None = None
    default_requests: list[dict[str, Any]] | None = None
    default_observation_plans: list[dict[str, Any]] | None = None
    catalog_queries: list[dict[str, Any]] | None = None
    observation_plans: list[dict[str, Any]] | None = None
    gcn_triggers: list[dict[str, Any]] | None = None
    ephemeris: EphemerisResponse | None = None
    telescope: TelescopeResponse | None = None


class ClassificationEditResponse(BaseModel):
    """An edit of a classification's probability."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    classification_id: int | None = None
    editor_id: int | None = None
    editor_name: str | None = None
    old_probability: float | None = None
    new_probability: float | None = None


class ClassificationVoteResponse(BaseModel):
    """A vote on a classification."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    classification_id: int | None = None
    voter_id: int | None = None
    vote: int | None = None


class TaxonomyResponse(BaseModel):
    """A classification taxonomy."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    version: str | None = None
    provenance: str | None = None
    is_latest: bool | None = Field(alias="isLatest", default=None)
    hierarchy: dict[str, Any] | None = None
    groups: list[GroupResponse] | None = None
    classifications: list[ClassificationResponse] | None = None


class ClassificationResponse(BaseModel):
    """A classification of a source."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str
    classification: str
    taxonomy_id: int
    probability: float | None = None
    author_name: str | None = None
    author_id: int | None = None
    origin: str | None = None
    ml: bool | None = None
    taxonomy: TaxonomyResponse | None = None
    votes: list[ClassificationVoteResponse] | None = None
    edits: list[ClassificationEditResponse] | None = None
    groups: list[GroupResponse] | None = None
    author: dict[str, Any] | None = None
    # typed as dict to avoid an import cycle with sources
    obj: dict[str, Any] | None = None


class CommentResponse(BaseModel):
    """A comment on a source, spectrum, GCN event, shift, or earthquake.

    Union of the Comment, CommentOnSpectrum, CommentOnGCN, CommentOnShift,
    and CommentOnEarthquake payloads, so each type-specific foreign key is
    optional.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    text: str | None = None
    channel: str | None = None
    system: bool | None = None
    attachment_name: str | None = None
    attachment_bytes: Any = None
    origin: str | None = None
    bot: bool | None = None
    author_id: int | None = None
    author: dict[str, Any] | None = None
    groups: list[GroupResponse] | None = None
    obj_id: str | None = None
    spectrum_id: int | None = None
    gcn_id: int | None = None
    earthquake_id: int | None = None
    shift_id: int | None = None
    # the package has no model for a bare Obj, and the modules that model the
    # other resources import this one
    obj: dict[str, Any] | None = None
    spectrum: dict[str, Any] | None = None
    gcn: dict[str, Any] | None = None
    shift: dict[str, Any] | None = None
    earthquake: dict[str, Any] | None = None
    dateobs: datetime | None = None
    resource_type: str | None = Field(alias="resourceType", default=None)


class EventObservationPlanStatisticsResponse(BaseModel):
    """Statistics (sky area, 2D probability, ...) derived from one plan.

    ``observation_plan`` stays untyped to avoid a recursive model.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    observation_plan_id: int | None = None
    localization_id: int | None = None
    statistics: dict[str, Any] = Field(default_factory=dict)
    observation_plan: dict[str, Any] | None = None


class PlannedObservationResponse(BaseModel):
    """A single planned exposure of an observation plan.

    The single-plan handler renames the ``field_id`` foreign key to
    ``field_db_id`` and puts the instrument's own field number in
    ``field_id``, then adds ``rise_time``/``set_time`` (empty strings when the
    field never rises or sets that night). ``observation_plan`` stays untyped
    to avoid a recursive model.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    observation_plan_id: int | None = None
    instrument_id: int | None = None
    dateobs: datetime | None = None
    field_id: int | None = None
    field_db_id: int | None = None
    exposure_time: int | None = None
    weight: float | None = None
    filt: str | None = None
    obstime: datetime | None = None
    overhead_per_exposure: int | None = None
    planned_observation_id: int | None = None
    rise_time: str | None = None
    set_time: str | None = None
    field: InstrumentFieldResponse | None = None
    instrument: InstrumentResponse | None = None
    observation_plan: dict[str, Any] | None = None


class SurveyEfficiencyForObservationPlanResponse(BaseModel):
    """An efficiency analysis run over an observation plan."""

    # As above, the four count/efficiency keys are properties injected by the
    # observation plan handler rather than mapper columns.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    lightcurves: str | None = None
    requester_id: int | None = None
    observation_plan_id: int | None = None
    number_of_transients: int | None = None
    number_in_covered: int | None = None
    number_detected: int | None = None
    efficiency: float | None = None
    requester: UserResponse | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    observation_plan: EventObservationPlanResponse | None = None


class EventObservationPlanResponse(BaseModel):
    """A generated observation plan.

    ``observation_plan_request`` stays untyped to avoid a recursive model.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    observation_plan_request_id: int | None = None
    instrument_id: int | None = None
    dateobs: datetime | None = None
    plan_name: str | None = None
    validity_window_start: datetime | None = None
    validity_window_end: datetime | None = None
    status: str | None = None
    statistics: list[EventObservationPlanStatisticsResponse] = Field(
        default_factory=list
    )
    planned_observations: list[PlannedObservationResponse] = Field(default_factory=list)
    survey_efficiency_analyses: list[SurveyEfficiencyForObservationPlanResponse] = (
        Field(default_factory=list)
    )
    instrument: InstrumentResponse | None = None
    observation_plan_request: dict[str, Any] | None = None


class FacilityTransactionRequestResponse(BaseModel):
    """A queued facility call (``FacilityTransactionRequest``)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    last_query: datetime | None = None
    method: str | None = None
    endpoint: str | None = None
    data: dict[str, Any] | None = None
    params: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    status: str | None = None
    followup_request_id: int | None = None
    observation_plan_request_id: int | None = None
    initiator_id: int | None = None
    initiator: UserResponse | None = None
    # parent rows, typed as dict to avoid recursion into this model and an
    # typed as dict to avoid an import cycle with followup_requests
    followup_request: dict[str, Any] | None = None
    observation_plan_request: dict[str, Any] | None = None


class FacilityTransactionResponse(BaseModel):
    """A serialized exchange with a facility (``FacilityTransaction``)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    request: dict[str, Any] | None = None
    response: dict[str, Any] | None = None
    followup_request_id: int | None = None
    observation_plan_request_id: int | None = None
    initiator_id: int | None = None
    initiator: UserResponse | None = None
    # parent rows, typed as dict to avoid recursion into this model and an
    # typed as dict to avoid an import cycle with followup_requests
    followup_request: dict[str, Any] | None = None
    observation_plan_request: dict[str, Any] | None = None


class LocalizationPropertyResponse(BaseModel):
    """Properties parsed from a localization."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    localization_id: int | None = None
    data: dict[str, Any] | None = None
    sent_by: UserResponse | None = None
    # typed as dict: LocalizationResponse owns this row, so typing the
    # back-reference would make the two models mutually recursive
    localization: dict[str, Any] | None = None


class LocalizationTagResponse(BaseModel):
    """A qualitative tag on a localization."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    localization_id: int | None = None
    text: str | None = None
    sent_by: UserResponse | None = None
    # typed as dict: LocalizationResponse owns this row, so typing the
    # back-reference would make the two models mutually recursive
    localization: dict[str, Any] | None = None


class LocalizationResponse(BaseModel):
    """A GCN event localization.

    ``uniq``, ``probdensity``, ``distmu``, ``distsigma``, ``distnorm`` and
    ``contour`` are deferred, so each is only present when the handler undefers
    it; the distance arrays are undeferred only by the single-localization
    endpoint, which also injects ``flat_2d`` (the rasterized 2D skymap) when
    ``include2DMap`` is set.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    dateobs: datetime | None = None
    localization_name: str | None = None
    uniq: list[int] | None = None
    probdensity: list[float] | None = None
    distmu: list[float | None] | None = None
    distsigma: list[float | None] | None = None
    distnorm: list[float | None] | None = None
    contour: dict[str, Any] | None = None
    notice_id: int | None = None
    flat_2d: list[float] | None = None
    sent_by: UserResponse | None = None
    properties: list[LocalizationPropertyResponse] | None = None
    tags: list[LocalizationTagResponse] | None = None
    # dicts: these rows all point back at the localization
    gcnevent: dict[str, Any] | None = None
    observationplan_requests: list[dict[str, Any]] | None = None
    survey_efficiency_analyses: list[dict[str, Any]] | None = None


class GcnEventCrossmatchStateResponse(BaseModel):
    """Alert-crossmatch progress for one event, filter and localization.

    ``status`` is one of ``"pending"``, ``"processing"``, ``"done"`` or
    ``"failed"``, but the column is a plain string, so it is not narrowed here.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    gcnevent_id: int | None = None
    filter_id: int | None = None
    localization_id: int | None = None
    last_queried: datetime | None = None
    last_alert_jd: float | None = None
    status: str | None = None
    error: str | None = None
    archival_done: bool | None = None
    n_matches: int | None = None
    filter: FilterResponse | None = None
    localization: LocalizationResponse | None = None
    gcnevent: dict[str, Any] | None = None


class LocalizationCenterResponse(BaseModel):
    """The center of a localization.

    ``ebv`` is the Schlegel-Finkbeiner-Davis reddening at that position, and is
    null when the dust map lookup fails.
    """

    model_config = ConfigDict(extra="forbid")

    ra: float | None = None
    dec: float | None = None
    gal_lat: float | None = None
    gal_lon: float | None = None
    ebv: float | None = None


class GcnEventLocalizationResponse(LocalizationResponse):
    """A localization as returned inside a GCN event payload.

    The single-event endpoint replaces the localization's ``tags`` and
    ``properties`` with explicitly serialized lists and adds ``center``; the
    paginated endpoint returns ``tags`` only.
    """

    tags: list[LocalizationTagResponse] | None = None
    properties: list[LocalizationPropertyResponse] | None = None
    center: LocalizationCenterResponse | None = None


class GcnEventUserResponse(BaseModel):
    """A user advocating for a GCN event.

    ``username``, ``first_name`` and ``last_name`` are copied off the joined
    user by the single-event endpoint, which returns these rows as
    ``event_users``.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    gcnevent_id: int | None = None
    user_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    user: UserResponse | None = None
    gcnevent: dict[str, Any] | None = None


class GcnNoticeResponse(BaseModel):
    """A GCN notice attached to an event.

    ``content`` is the raw notice body (XML, JSON or plain text), decoded from a
    deferred ``LargeBinary`` column: it is absent unless the handler undefers
    it, and the single-event endpoint drops it when ``excludeNoticeContent`` is
    set.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    dateobs: datetime | None = None
    ivorn: str | None = None
    notice_type: str | None = None
    notice_format: str | None = None
    stream: str | None = None
    date: datetime | None = None
    content: Any = None
    has_localization: bool | None = None
    localization_ingested: bool | None = None
    sent_by: UserResponse | None = None
    gcnevent: dict[str, Any] | None = None


class GcnPropertyResponse(BaseModel):
    """Properties parsed from an event notice."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    dateobs: datetime | None = None
    data: dict[str, Any] | None = None
    sent_by: UserResponse | None = None
    gcnevent: dict[str, Any] | None = None


class GcnReportResponse(BaseModel):
    """A structured (publishable) report on a GCN event.

    ``data`` is a deferred JSONB column, undeferred by the single-report
    endpoint. It holds ``{"status": "pending"}`` while the report is being
    assembled and a JSON string once the background writer has stored the
    rendered report, so both forms are accepted.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    dateobs: datetime | None = None
    group_id: int | None = None
    report_name: str | None = None
    data: dict[str, Any] | str | None = None
    published: bool | None = None
    sent_by: UserResponse | None = None
    group: GroupResponse | None = None
    gcnevent: dict[str, Any] | None = None


class GcnSummaryResponse(BaseModel):
    """A human-readable summary of a GCN event.

    ``text`` is deferred and is undeferred by the single-summary endpoint; it
    reads ``"pending"`` until the background writer fills it in.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    dateobs: datetime | None = None
    group_id: int | None = None
    title: str | None = None
    text: str | None = None
    sent_by: UserResponse | None = None
    group: GroupResponse | None = None
    gcnevent: dict[str, Any] | None = None


class GcnTriggerResponse(BaseModel):
    """Whether a GCN event triggered an allocation."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    dateobs: datetime | None = None
    allocation_id: int | None = None
    triggered: bool | None = None
    allocation: AllocationResponse | None = None
    gcnevent: dict[str, Any] | None = None


class ObservationPlanRequestResponse(BaseModel):
    """A request for an observation plan."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    requester_id: int | None = None
    last_modified_by_id: int | None = None
    gcnevent_id: int | None = None
    localization_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    allocation_id: int | None = None
    combined_id: str | None = None
    default_plan: bool | None = None
    observation_plans: list[EventObservationPlanResponse] = Field(default_factory=list)
    allocation: AllocationResponse | None = None
    gcnevent: GcnEventResponse | None = None
    localization: LocalizationResponse | None = None
    requester: UserResponse | None = None
    last_modified_by: UserResponse | None = None
    target_groups: list[GroupResponse] = Field(default_factory=list)
    transactions: list[FacilityTransactionResponse] = Field(default_factory=list)
    transaction_requests: list[FacilityTransactionRequestResponse] = Field(
        default_factory=list
    )


class ReminderResponse(BaseModel):
    """A reminder on a source, spectrum, GCN event, shift, or earthquake.

    Union of the Reminder, ReminderOnSpectrum, ReminderOnGCN, ReminderOnShift,
    and ReminderOnEarthquake payloads, so each type-specific foreign key is
    optional.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    text: str | None = None
    origin: str | None = None
    bot: bool | None = None
    next_reminder: datetime | None = None
    reminder_delay: float | None = None
    number_of_reminders: int | None = None
    user_id: int | None = None
    user: dict[str, Any] | None = None
    groups: list[GroupResponse] | None = None
    obj_id: str | None = None
    spectrum_id: int | None = None
    gcn_id: int | None = None
    earthquake_id: int | None = None
    shift_id: int | None = None
    # the package has no model for a bare Obj, and the modules that model the
    # other resources import this one
    obj: dict[str, Any] | None = None
    spectrum: dict[str, Any] | None = None
    gcn: dict[str, Any] | None = None
    shift: dict[str, Any] | None = None
    earthquake: dict[str, Any] | None = None


class SurveyEfficiencyForObservationsResponse(BaseModel):
    """An efficiency analysis run over a set of executed observations."""

    # ``number_of_transients``, ``number_in_covered``, ``number_detected`` and
    # ``efficiency`` are properties derived from ``lightcurves``, not columns:
    # the survey efficiency handlers omit them, while the GCN event and
    # observation plan handlers add them to the serialized row.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    lightcurves: str | None = None
    requester_id: int | None = None
    gcnevent_id: int | None = None
    localization_id: int | None = None
    instrument_id: int | None = None
    number_of_transients: int | None = None
    number_in_covered: int | None = None
    number_detected: int | None = None
    efficiency: float | None = None
    requester: UserResponse | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    gcnevent: GcnEventResponse | None = None
    localization: LocalizationResponse | None = None
    instrument: InstrumentResponse | None = None


class GcnEventResponse(BaseModel):
    """A GCN event, keyed by its UTC observation time.

    ``tags`` (the distinct texts of the event's ``GcnTag`` rows) and
    ``lightcurve`` (a URL parsed out of the first notice) are properties the
    handlers inject rather than columns; the underlying ``_tags`` relationship
    is never serialized. ``circulars``, ``gracedb_log`` and ``gracedb_labels``
    are deferred, so they only appear when a handler undefers them.
    ``event_users_ids`` is a column property aggregating ``gcnevent_users``,
    and ``event_users`` is the same join rows with the user's name copied in.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sent_by_id: int | None = None
    dateobs: datetime | None = None
    trigger_id: str | None = None
    aliases: list[str] | None = None
    tach_id: str | None = None
    circulars: dict[str, str] | None = None
    gracedb_log: dict[str, Any] | None = None
    gracedb_labels: dict[str, Any] | None = None
    lightcurve: str | None = None
    event_users_ids: list[int] | None = None
    tags: list[str] | None = None
    localizations: list[GcnEventLocalizationResponse] | None = None
    gcn_notices: list[GcnNoticeResponse] | None = None
    properties: list[GcnPropertyResponse] | None = None
    summaries: list[GcnSummaryResponse] | None = None
    reports: list[GcnReportResponse] | None = None
    comments: list[CommentResponse] | None = None
    reminders: list[ReminderResponse] | None = None
    detectors: list[MMADetectorResponse] | None = None
    gcn_triggers: list[GcnTriggerResponse] | None = None
    event_users: list[GcnEventUserResponse] | None = None
    gcnevent_users: list[GcnEventUserResponse] | None = None
    users: list[UserResponse] | None = None
    groups: list[GroupResponse] | None = None
    sent_by: UserResponse | None = None
    observationplan_requests: list[ObservationPlanRequestResponse] | None = None
    survey_efficiency_analyses: list[SurveyEfficiencyForObservationsResponse] | None = (
        None
    )
    crossmatch_states: list[GcnEventCrossmatchStateResponse] | None = None


InstrumentResponse.model_rebuild()
ObservationPlanRequestResponse.model_rebuild()
SurveyEfficiencyForObservationPlanResponse.model_rebuild()
SurveyEfficiencyForObservationsResponse.model_rebuild()
TaxonomyResponse.model_rebuild()
TelescopeResponse.model_rebuild()
GroupResponse.model_rebuild()
GroupUserResponse.model_rebuild()
