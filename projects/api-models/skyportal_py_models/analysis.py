"""Response models for ``/api/analysis_service`` and ``/api/obj/analysis``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.users import UserResponse

AnalysisType = Literal["lightcurve_fitting", "spectrum_fitting", "meta_analysis"]


AnalysisInputType = Literal[
    "photometry",
    "spectra",
    "redshift",
    "annotations",
    "comments",
    "classifications",
]


AuthenticationType = Literal[
    "none",
    "header_token",
    "api_key",
    "HTTPBasicAuth",
    "HTTPDigestAuth",
    "OAuth1",
]


WebhookStatus = Literal[
    "queued",
    "pending",
    "completed",
    "failure",
    "cancelled",
    "timed_out",
]


class AnalysisServiceResponse(BaseModel):
    """An external analysis service (``AnalysisService``)."""

    # ``_authinfo`` is an underscore-prefixed column and so is never part of
    # ``to_dict()``; the ``obj_analyses`` and ``default_analyses`` backrefs are
    # never eager-loaded by the handlers.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    version: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    url: str | None = None
    optional_analysis_parameters: dict[str, Any] | str | None = None
    authentication_type: AuthenticationType | None = None
    enabled: bool | None = None
    analysis_type: AnalysisType | None = None
    input_data_types: list[AnalysisInputType] = Field(default_factory=list)
    timeout: float | None = None
    upload_only: bool | None = None
    display_on_resource_dropdown: bool | None = None
    is_summary: bool | None = None
    groups: list[GroupResponse] = Field(default_factory=list)


class AnalysisServicePostResponse(BaseModel):
    """Result of registering an analysis service."""

    model_config = ConfigDict(extra="forbid")

    id: int


class ObjAnalysisResponse(BaseModel):
    """An analysis run on an object (``ObjAnalysis``)."""

    # Underscore-prefixed columns (``_unique_id``, ``_full_name``) never appear
    # in ``to_dict()``; ``_full_name`` is surfaced separately as ``filename``
    # when ``includeFilename`` is set. ``analysis_service_name``,
    # ``analysis_service_description``, ``num_plots``, ``filename``, ``data``,
    # ``model_lightcurve``, ``model_lightcurves``, ``model_name`` and
    # ``n_detections`` are injected by the handler rather than being columns.
    # The listing endpoint without ``objID`` returns only ``id``, ``obj_id``,
    # ``status``, ``status_message``, ``created_at``, ``last_activity`` and
    # ``analysis_service_id`` (plus the two service-name keys).

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    author_id: int | None = None
    analysis_service_id: int | None = None
    hash: str | None = None
    show_parameters: bool | None = None
    show_plots: bool | None = None
    show_corner: bool | None = None
    analysis_parameters: dict[str, Any] | None = None
    input_filters: dict[str, Any] | None = None
    invalid_after: datetime | None = None
    token: str | None = None
    handled_by_url: str | None = None
    status: WebhookStatus | None = None
    status_message: str | None = None
    duration: float | None = None
    last_activity: datetime | None = None
    analysis_service_name: str | None = None
    analysis_service_description: str | None = None
    num_plots: int | None = None
    filename: str | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    data: dict[str, Any] | None = None
    model_lightcurve: Any = None
    model_lightcurves: Any = None
    model_name: str | None = None
    n_detections: int | None = None


class AnalysisPostResponse(BaseModel):
    """Result of starting an analysis run."""

    model_config = ConfigDict(extra="forbid")

    id: int


class AnalysisUploadResponse(BaseModel):
    """Result of uploading an upload-only analysis."""

    model_config = ConfigDict(extra="forbid")

    id: int
    message: str | None = None


class DefaultAnalysisResponse(BaseModel):
    """A default analysis (``DefaultAnalysis``)."""

    # The handler eager-loads ``groups``, ``author`` and ``analysis_service``.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    analysis_service_id: int | None = None
    author_id: int | None = None
    show_parameters: bool | None = None
    show_plots: bool | None = None
    show_corner: bool | None = None
    default_analysis_parameters: dict[str, Any] | None = None
    source_filter: dict[str, Any] | None = None
    stats: dict[str, Any] | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    author: UserResponse | None = None
    analysis_service: AnalysisServiceResponse | None = None


class DefaultAnalysisPostResponse(BaseModel):
    """Result of creating a default analysis."""

    model_config = ConfigDict(extra="forbid")

    id: int


class AnalysisServicePost(BaseModel):
    """Payload for registering a new analysis service."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    name: str
    url: str
    authentication_type: AuthenticationType
    analysis_type: AnalysisType
    input_data_types: list[AnalysisInputType]
    display_name: str | None = None
    description: str | None = None
    version: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    optional_analysis_parameters: str | None = None
    authinfo: str | None = Field(alias="_authinfo", default=None)
    enabled: bool | None = None
    timeout: float | None = None
    upload_only: bool | None = None
    is_summary: bool | None = None
    display_on_resource_dropdown: bool | None = None
    group_ids: list[int] | None = None


class AnalysisServiceUpdate(BaseModel):
    """Payload for a partial update of an analysis service."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    url: str | None = None
    authentication_type: AuthenticationType | None = None
    analysis_type: AnalysisType | None = None
    input_data_types: list[AnalysisInputType] | None = None
    display_name: str | None = None
    description: str | None = None
    version: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    optional_analysis_parameters: str | None = None
    authinfo: dict[str, Any] | None = None
    enabled: bool | None = None
    timeout: float | None = None
    upload_only: bool | None = None
    is_summary: bool | None = None
    display_on_resource_dropdown: bool | None = None
    group_ids: list[int] | None = None


class AnalysisPost(BaseModel):
    """Payload for starting an analysis run."""

    model_config = ConfigDict(extra="forbid")

    analysis_parameters: dict[str, Any] | None = None
    show_parameters: bool | None = None
    show_plots: bool | None = None
    show_corner: bool | None = None
    input_filters: dict[str, Any] | None = None
    group_ids: list[int] | None = None


class AnalysisUploadPost(BaseModel):
    """Payload for uploading results to an upload-only analysis service."""

    model_config = ConfigDict(extra="forbid")

    analysis: dict[str, Any] | None = None
    message: str | None = None
    show_parameters: bool | None = None
    show_plots: bool | None = None
    show_corner: bool | None = None
    group_ids: list[int] | None = None


class DefaultAnalysisPost(BaseModel):
    """Payload for creating or updating a default analysis."""

    model_config = ConfigDict(extra="forbid")

    default_analysis_parameters: dict[str, Any] | None = None
    source_filter: dict[str, Any] | None = None
    daily_limit: int | None = None
    show_parameters: bool | None = None
    show_plots: bool | None = None
    show_corner: bool | None = None
    group_ids: list[int] | None = None


class AnalysisServicePostBody(BaseModel):
    """Request body for creating an Analysis Service."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None, description="Unique name/identifier of the analysis service."
    )
    display_name: str | None = Field(
        default=None, description="Display name of the analysis service."
    )
    description: str | None = Field(
        default=None, description="Description of the analysis service."
    )
    version: str | None = Field(
        default=None,
        description="Semantic version (or githash) of the analysis service.",
    )
    contact_name: str | None = Field(
        default=None,
        description="Name of person responsible for the service (ie. the "
        "maintainer). This person does not need to be part of this SkyPortal "
        "instance.",
    )
    contact_email: str | None = Field(
        default=None,
        description="Email address of the person responsible for the service.",
    )
    url: str | None = Field(
        default=None,
        description="URL to running service accessible to this SkyPortal instance. "
        "For example, http://localhost:5000/analysis/<service_name>.",
    )
    optional_analysis_parameters: str | dict[str, Any] | None = Field(
        default=None,
        description="Optional URL parameters that can be passed to the service, "
        "along with a list of possible values (to be used in a dropdown UI).",
    )
    authentication_type: str | None = Field(
        default=None,
        description="Service authentication method. See "
        "https://docs.python-requests.org/en/master/user/authentication/",
    )
    authinfo: str | None = Field(
        default=None,
        alias="_authinfo",
        description="Authentication secrets for the service. Not needed if "
        'authentication_type is "none". This should be a string that can be '
        "parsed by the python json.loads() function and should contain the key "
        "`authentication_type`.",
    )
    enabled: bool | None = Field(
        default=None, description="Whether the service is enabled or not."
    )
    analysis_type: str | None = Field(default=None, description="Type of analysis.")
    input_data_types: list[str] | None = Field(
        default=None,
        description="List of input data types that the service requires.",
    )
    timeout: float | None = Field(
        default=None,
        description="Max time in seconds to wait for the analysis service to "
        "complete. Default is 3600.0.",
    )
    is_summary: bool | None = Field(
        default=None,
        description="Establishes that analysis results on the resource should be "
        "considered a summary.",
    )
    display_on_resource_dropdown: bool | None = Field(
        default=None,
        description="Show this analysis service on the analysis dropdown of the "
        "resource.",
    )
    upload_only: bool | None = Field(
        default=None,
        description="If true, the analysis service is an upload type, where the "
        "user provides the input data.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to use the Analysis Service. Defaults to all of requesting user's "
        "groups.",
    )


class AnalysisServicePatchBody(AnalysisServicePostBody):
    """Request body for updating an Analysis Service (all fields optional)."""


class AnalysisPostBody(BaseModel):
    """Request body for running an analysis."""

    model_config = ConfigDict(extra="forbid")

    show_parameters: bool = Field(
        default=False, description="Whether to render the parameters of this analysis."
    )
    show_plots: bool = Field(
        default=False, description="Whether to render the plots of this analysis."
    )
    show_corner: bool = Field(
        default=False,
        description="Whether to render the corner plots of this analysis.",
    )
    input_filters: dict[str, Any] | None = Field(
        default_factory=dict, description="Filters to apply to the input data."
    )
    analysis_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of parameters to be passed thru to the analysis.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view analysis results. Defaults to all of requesting user's "
        "groups.",
    )


class AnalysisUploadBody(BaseModel):
    """Request body for uploading an upload_only analysis result."""

    model_config = ConfigDict(extra="forbid")

    analysis: dict[str, Any] = Field(
        default_factory=dict, description="Results data of this analysis."
    )
    message: str = Field(
        default="", description="Status message to store with the analysis."
    )
    show_parameters: bool = Field(
        default=True, description="Whether to render the parameters of this analysis."
    )
    show_plots: bool = Field(
        default=True, description="Whether to render the plots of this analysis."
    )
    show_corner: bool = Field(
        default=True,
        description="Whether to render the corner plots of this analysis.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view analysis results. Defaults to all of requesting user's "
        "groups.",
    )


class DefaultAnalysisPostBody(BaseModel):
    """Request body for creating a default analysis."""

    model_config = ConfigDict(extra="forbid")

    default_analysis_parameters: dict[str, Any] | str = Field(
        default_factory=dict,
        description="Dictionary of parameters to be passed thru to the analysis.",
    )
    source_filter: dict[str, Any] | str = Field(
        default_factory=dict,
        description="Dictionary of filters to apply to the input data.",
    )
    daily_limit: int | str = Field(
        default=10, description="Maximum number of analyses to run per day."
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view analysis results. Defaults to all of requesting user's "
        "groups.",
    )
    show_parameters: bool = Field(
        default=True, description="Whether to render the parameters of this analysis."
    )
    show_plots: bool = Field(
        default=True, description="Whether to render the plots of this analysis."
    )
    show_corner: bool = Field(
        default=True,
        description="Whether to render the corner plots of this analysis.",
    )


class DefaultAnalysisPatchBody(BaseModel):
    """Request body for updating a default analysis (all fields optional)."""

    model_config = ConfigDict(extra="forbid")

    default_analysis_parameters: dict[str, Any] | str | None = Field(
        default=None,
        description="Dictionary of parameters to be passed thru to the analysis.",
    )
    source_filter: dict[str, Any] | str | None = Field(
        default=None, description="Dictionary of filters to apply to the input data."
    )
    daily_limit: int | str | None = Field(
        default=None, description="Maximum number of analyses to run per day."
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view analysis results.",
    )
    show_parameters: bool | None = Field(
        default=None, description="Whether to render the parameters of this analysis."
    )
    show_plots: bool | None = Field(
        default=None, description="Whether to render the plots of this analysis."
    )
    show_corner: bool | None = Field(
        default=None, description="Whether to render the corner plots of this analysis."
    )


class AnalysisGetQuery(BaseModel):
    """Query parameters for retrieving analyses."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset(
        {"objID", "includeFilename", "includeAnalysisData"}
    )

    objID: str | None = Field(
        default=None,
        description="Return any analysis on an object with ID objID",
    )
    analysisServiceID: int | None = Field(
        default=None,
        description=(
            "ID of the analysis service used to create the analysis, used only "
            "if no analysis_id is given"
        ),
    )
    includeAnalysisData: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include the data associated with the "
            "analysis in the response. Could be a large amount of data. Only "
            "works for single analysis requests. Defaults to false."
        ),
    )
    summaryOnly: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to return only analyses that use analysis "
            "services with `is_summary` set to true. Defaults to false."
        ),
    )
    includeFilename: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include the filename of the data "
            "associated with the analysis in the response. Defaults to false."
        ),
    )


class AnalysisProductsGetQuery(BaseModel):
    """Query parameters for retrieving an analysis product."""

    model_config = ConfigDict(extra="forbid")

    download: bool = Field(
        default=False,
        description="Download the results as a file",
    )


class AnalysisWebhookPostBody(BaseModel):
    """Result payload posted back by an external analysis service.

    External services may include additional keys, so extras are allowed
    rather than forbidden.
    """

    model_config = ConfigDict(extra="allow")

    status: str | None = Field(
        default=None, description="Status of the analysis run, e.g. 'success'."
    )
    message: str | None = Field(
        default=None,
        description="Status/return message from the analysis service.",
    )
    analysis: dict[str, Any] | None = Field(
        default=None, description="Results data of this analysis."
    )
