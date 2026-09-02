"""Response models for ``/api/brokers``."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from skyportal_py_models.streams import StreamResponse

#: How a provider models filters, so a client can pick an editor.
BrokerFilterKind = Literal["pipeline", "query", "tags", "none"]


class BrokerCapabilitiesResponse(BaseModel):
    """What a broker's provider class implements (see ``implements()``)."""

    model_config = ConfigDict(extra="forbid")

    query_alerts: bool | None = None
    get_alert: bool | None = None
    get_cutouts: bool | None = None
    cone_search: bool | None = None
    get_filters: bool | None = None
    create_filter: bool | None = None
    update_filter: bool | None = None
    delete_filter: bool | None = None
    test_filter: bool | None = None
    validate_filter: bool | None = None
    filter_modules: bool | None = None
    run_ingestion: bool | None = None
    validate_config: bool | None = None
    test_connection: bool | None = None
    save_as_source: bool | None = None
    get_photometry: bool | None = None
    # Data-semantics flags rather than methods: whether ``cone_search``
    # returns reference catalogs, and the dialect ``test_filter`` expects its
    # pipeline in (``None`` when the provider takes no pipeline at all).
    cross_match_catalogs: bool | None = None
    filter_pipeline: str | None = None


class BrokerResponse(BaseModel):
    """A configured connection to an external alert broker.

    ``broker_to_dict`` hand-builds this payload rather than calling
    ``to_dict()``, so ``created_at``/``modified`` are never returned even though
    the row carries them. ``altdata`` is only present for system admins, with
    the provider's secret config fields stripped out.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str | None = None
    broker_classname: (
        Literal[
            "GENERICBROKER",
            "LASAIRBROKER",
            "BABAMULBROKER",
            "BOOMBROKER",
            "FINKBROKER",
            "ALERCEBROKER",
            "ANTARESBROKER",
            "PITTGOOGLEBROKER",
            "AMPELBROKER",
        ]
        | None
    ) = None
    active: bool | None = None
    default_alert_search: bool | None = None
    default_crossmatch: bool | None = None
    capabilities: BrokerCapabilitiesResponse | None = None
    surveys: list[str] = Field(default_factory=list)
    filter_kind: BrokerFilterKind | None = None
    # Free-form per-instance provider configuration (endpoints, credentials).
    altdata: dict[str, Any] | None = None


class BrokerPostResponse(BaseModel):
    """Result of registering a broker."""

    model_config = ConfigDict(extra="forbid")

    id: int


class BrokerAlertSaveResponse(BaseModel):
    """Result of saving a broker alert as a source."""

    model_config = ConfigDict(extra="forbid")

    id: str


class BrokerFilterValidationResponse(BaseModel):
    """Verdict of a broker filter version validation."""

    model_config = ConfigDict(extra="forbid")

    fid: str | int | None = None
    passed: bool | None = None
    message: str | None = None


class BrokerFilterVersionResponse(BaseModel):
    """One editable version of a broker filter, as stored on the filter row."""

    model_config = ConfigDict(extra="forbid")

    fid: str | int | None = None
    # The version tree the broker's own filter language defines; skyportal
    # stores it verbatim, so its shape is the provider's, not skyportal's.
    version: Any = None


class BrokerFilterResponse(BaseModel):
    """A skyportal ``Filter`` as listed by the broker endpoints.

    The handlers hand-build this payload, so it carries a strict subset of the
    ``Filter`` columns and never ``created_at``/``modified``. ``altdata`` stays
    free-form: it holds the broker-side ids and the compiled native filter,
    whose shape the broker defines.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str | None = None
    group_id: int | None = None
    stream_id: int | None = None
    broker_id: int | None = None
    autosave: bool | None = None
    altdata: dict[str, Any] | None = None


class BrokerFilterDetailResponse(BaseModel):
    """A broker filter enriched with its broker-side versions and state.

    ``stream`` is trimmed by the handler to the stream's ``id`` and ``name``.
    ``fv`` comes straight back from the broker, so its entries are shaped by
    the provider rather than by skyportal. The ``fv``/``active_fid``/
    ``active``/``filters`` block is dropped entirely when the broker is
    unreachable or the filter has no broker-side counterpart.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str | None = None
    group_id: int | None = None
    broker_id: int | None = None
    autosave: bool | None = None
    stream: StreamResponse | None = None
    altdata: dict[str, Any] | None = None
    fv: list[dict[str, Any]] | None = None
    active_fid: str | int | None = None
    active: bool | None = None
    filters: list[BrokerFilterVersionResponse] | None = None


class BrokerFilterPostResponse(BaseModel):
    """Result of creating a broker filter version."""

    model_config = ConfigDict(extra="forbid")

    id: int
    altdata: dict[str, Any] | None = None
    autosave: bool | None = None


class BrokerFiltersPageResponse(BaseModel):
    """One page of results from the broker filter catalog."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    filters: list[BrokerFilterResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)


class BrokerFilterAttachResponse(BaseModel):
    """Result of attaching a filter to a broker."""

    model_config = ConfigDict(extra="forbid")

    id: int
    broker_id: int | None = None


#: The registered ``BrokerAPI`` provider classes (upstream ``BROKERS``).
BrokerClassname = Literal[
    "GENERICBROKER",
    "LASAIRBROKER",
    "BABAMULBROKER",
    "BOOMBROKER",
    "FINKBROKER",
    "ALERCEBROKER",
    "ANTARESBROKER",
    "PITTGOOGLEBROKER",
    "AMPELBROKER",
]


class BrokerPost(BaseModel):
    """Payload for registering a broker."""

    model_config = ConfigDict(extra="forbid")

    name: str
    broker_classname: BrokerClassname
    altdata: dict[str, Any] | None = None
    active: bool | None = None
    default_alert_search: bool | None = None
    default_crossmatch: bool | None = None


class BrokerFilterQuery(BaseModel):
    """A saved query for a broker whose ``filter_kind`` is ``"query"``."""

    model_config = ConfigDict(extra="forbid")

    selected: str
    tables: str
    conditions: str | None = None


# Custom filter-module element types; the store is provider-owned.
_FILTER_MODULE_ELEMENTS = ("variables", "listVariables", "switchCases", "blocks")


DEFAULT_FILTERS_PER_PAGE = 25


MAX_FILTERS_PER_PAGE = 100


class BrokerPostBody(BaseModel):
    """Request body for creating a broker."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Name of the broker connection.")
    broker_classname: str | None = Field(
        default=None, description="A registered BrokerAPI provider class name."
    )
    altdata: dict[str, Any] = Field(
        default_factory=dict,
        description="Endpoints/credentials for this broker instance.",
    )
    active: bool = Field(
        default=True, description="Whether the broker connection is active."
    )
    default_alert_search: bool = Field(
        default=False,
        description="Make this the broker the source page searches alerts on.",
    )
    default_crossmatch: bool = Field(
        default=False, description="Make this the broker cross-matches are run against."
    )


class BrokerPatchBody(BaseModel):
    """Request body for updating a broker."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Name of the broker connection.")
    active: bool | None = Field(
        default=None, description="Whether the broker connection is active."
    )
    altdata: dict[str, Any] | None = Field(
        default=None, description="Endpoints/credentials for this broker instance."
    )
    default_alert_search: bool | None = Field(
        default=None,
        description="Make this the broker the source page searches alerts on.",
    )
    default_crossmatch: bool | None = Field(
        default=None, description="Make this the broker cross-matches are run against."
    )


class BrokerSaveBody(BaseModel):
    """Request body for saving a broker alert as a source."""

    model_config = ConfigDict(extra="forbid")

    group_ids: list[int] | None = Field(
        default=None, description="Group IDs the saved source should belong to."
    )


class BrokerFilterTestBody(RootModel[dict[str, Any]]):
    """Filter parameters specific to the broker's filter_kind, passed through to
    the provider (e.g. Lasair's selected/tables/conditions, BOOM's pipeline)."""


class BrokerFilterValidateBody(BaseModel):
    """Request body for validating a broker filter version for activation."""

    model_config = ConfigDict(extra="forbid")

    # BOOM issues string fids; Lasair-style numeric ones are also accepted.
    fid: int | str | None = Field(
        default=None, description="Filter version id (fid) to validate."
    )


class BrokerFilterModuleWriteBody(BaseModel):
    """Request body for creating/updating a broker custom filter module."""

    model_config = ConfigDict(extra="forbid")

    elements: str | None = Field(
        default=None,
        description="Custom filter-module element type "
        "(one of variables/listVariables/switchCases/blocks).",
    )
    data: dict[str, Any] | None = Field(
        default=None, description="The module payload to store."
    )


class BrokerFiltersPostBody(BaseModel):
    """Request body for creating a broker filter version."""

    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = Field(
        default=None,
        description="Query-kind (e.g. Lasair) filter with selected/tables/conditions.",
    )
    altdata: list[Any] | None = Field(
        default=None,
        description="Compiled native filter forwarded to the broker, as an "
        "aggregation pipeline: a list of stages, not a mapping.",
    )
    filters: Any = Field(
        default=None,
        description="Editable version tree stored alongside the broker filter id.",
    )
    name: str | None = Field(
        default=None,
        description="Filter name (informational; the skyportal Filter name is "
        "used server-side).",
    )
    autosave: bool | None = Field(
        default=None,
        description="Whether candidates passing the filter are auto-saved as sources.",
    )


class BrokerFiltersPatchBody(BaseModel):
    """Request body for updating a broker filter."""

    model_config = ConfigDict(extra="forbid")

    active: bool | None = Field(
        default=None, description="Whether the selected filter version is active."
    )
    active_fid: int | str | None = Field(
        default=None, description="Filter version id (fid) to activate."
    )
    autoAnnotate: bool | None = Field(
        default=None, description="Whether to auto-annotate on filter passage."
    )
    autoSave: bool | None = Field(
        default=None, description="Whether to auto-save on filter passage."
    )
    autoFollowup: bool | None = Field(
        default=None, description="Whether to auto-trigger followup on filter passage."
    )
    autoSaveIgnoreGroupIds: list[int] | None = Field(
        default=None,
        description="Groups whose members are not auto-saved (e.g. junk).",
    )
    autoSaveIgnoreRadius: float | str | None = Field(
        default=None,
        description="Skip auto-save if a junk-group source lies within this "
        "many arcsec. Null or empty string clears it.",
    )
    autoSaveSaverId: int | str | None = Field(
        default=None,
        description="User the auto-saves are attributed to; must be a member "
        "of the filter's group. Null or empty string clears it.",
    )
    autoSaveComment: str | None = Field(
        default=None,
        description="Comment posted on each auto-save. Null or empty string clears it.",
    )
    autoFollowupDefaultId: int | str | None = Field(
        default=None,
        description="DefaultFollowupRequest the filter's auto-followup uses. "
        "Null or empty string clears it.",
    )


class BrokerFilterAttachBody(BaseModel):
    """Request body for attaching a filter to a broker."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int = Field(description="ID of the broker to attach the filter to.")


class BrokerConeSearchGetQuery(BaseModel):
    """Query parameters for a broker cone search."""

    model_config = ConfigDict(extra="forbid")

    ra: float = Field(description="RA in degrees (0 <= ra < 360).")
    dec: float = Field(description="Declination in degrees (-90 <= dec <= 90).")
    radius: float = Field(description="Search radius, in `radius_units`.")
    radius_units: Literal["deg", "arcmin", "arcsec"] = Field(
        default="arcsec",
        description="Units of `radius`. Defaults to arcsec.",
    )


class BrokerPhotometryGetQuery(BaseModel):
    """Query parameters for displaying an object's photometry via a broker."""

    model_config = ConfigDict(extra="forbid")

    survey: str | None = Field(
        default=None,
        description="Survey the photometry is fetched for.",
    )
    format: Literal["mag", "flux", "both"] = Field(
        default="mag", description="Photometry format."
    )
    magsys: Literal["jla1", "ab", "vega", "bd17", "csp", "ab-b12"] = Field(
        default="ab", description="Magnitude system."
    )
    refresh: bool = Field(
        default=False,
        description="Bypass any cached broker payload and re-fetch.",
    )


class BrokerSurveyPhotometryGetQuery(BrokerPhotometryGetQuery):
    """Query parameters for displaying an object's photometry via its survey's
    broker. The includeOwnerInfo/includeStreamInfo/includeValidationInfo/
    includeExtinction/includeSuperObjsPhotometry flags of
    GET /sources/{id}/photometry are accepted and
    ignored, so this endpoint can be dropped in as `photometry_display_endpoint`
    for the source page, which sends them."""

    survey: str = Field(
        min_length=1,
        description="Survey whose configured broker serves the photometry.",
    )
    includeOwnerInfo: bool = Field(default=False, description="Ignored.")
    includeStreamInfo: bool = Field(default=False, description="Ignored.")
    includeValidationInfo: bool = Field(default=False, description="Ignored.")
    includeExtinction: bool = Field(default=False, description="Ignored.")
    includeSuperObjsPhotometry: bool = Field(default=False, description="Ignored.")


class BrokerFilterModulesGetQuery(BaseModel):
    """Query parameters for reading a broker's filter-building vocabulary."""

    model_config = ConfigDict(extra="forbid")

    survey: str | None = Field(
        default=None,
        description="Survey whose filter modules to return.",
    )
    elements: Literal["schema", *_FILTER_MODULE_ELEMENTS] = Field(
        default="schema",
        description="Element type to return. Defaults to the alert schema.",
    )


class BrokerFilterCatalogGetQuery(BaseModel):
    """Query parameters for listing filters and their broker."""

    model_config = ConfigDict(extra="forbid")

    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=DEFAULT_FILTERS_PER_PAGE,
        description=(
            f"Number of filters to return per paginated request. Defaults to "
            f"{DEFAULT_FILTERS_PER_PAGE}. Capped at {MAX_FILTERS_PER_PAGE}."
        ),
    )
    name: str | None = Field(
        default=None,
        description="Case-insensitive substring of the filter name.",
    )
    groupID: int | None = Field(default=None, description="Filter by group ID.")
    streamID: int | None = Field(default=None, description="Filter by stream ID.")
    # not an int: the handler also accepts the literal "none" for unattached filters
    brokerID: str | None = Field(
        default=None,
        description='A broker id, or "none" for filters attached to no broker.',
    )
