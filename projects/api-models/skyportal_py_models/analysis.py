"""Response models for ``/api/analysis_service`` and ``/api/obj/analysis``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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
