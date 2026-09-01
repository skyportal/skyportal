"""Response models for ``/api/instrument``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import InstrumentFieldResponse, InstrumentResponse


class InstrumentLogResponse(BaseModel):
    """A log uploaded for an instrument."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    instrument_id: int | None = None
    instrument: InstrumentResponse | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    log: dict[str, Any] | None = None


class InstrumentPost(BaseModel):
    """Payload for creating an instrument."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    telescope_id: int
    band: str | None = None
    filters: list[str] = Field(default_factory=list)
    sensitivity_data: dict[str, Any] | None = None
    configuration_data: dict[str, Any] | None = None
    api_classname: str | None = None
    api_classname_obsplan: str | None = None
    listener_classname: str | None = None
    treasuremap_id: int | None = None
    tns_id: int | None = None
    across_id: str | None = None
    region: str | None = None
    field_data: dict[str, list[Any]] | str | None = None
    field_region: str | None = None
    field_fov_type: str | None = None
    field_fov_attributes: list[float] | float | None = None
    references: dict[str, list[Any]] | str | None = None


class InstrumentPut(BaseModel):
    """Payload for updating an instrument."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    type: str | None = None
    telescope_id: int | None = None
    band: str | None = None
    filters: list[str] | None = None
    sensitivity_data: dict[str, Any] | None = None
    configuration_data: dict[str, Any] | None = None
    api_classname: str | None = None
    api_classname_obsplan: str | None = None
    listener_classname: str | None = None
    treasuremap_id: int | None = None
    tns_id: int | None = None
    across_id: str | None = None
    region: str | None = None
    field_data: dict[str, list[Any]] | str | None = None
    field_region: str | None = None
    field_fov_type: str | None = None
    field_fov_attributes: list[float] | float | None = None
    references: dict[str, list[Any]] | str | None = None


class InstrumentGetQuery(BaseModel):
    """Query parameters for retrieving one or all instruments."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "includeGeoJSON",
            "includeGeoJSONSummary",
            "includeRegion",
            "ignoreCache",
            "localizationDateobs",
            "localizationName",
            "localizationCumprob",
            "airmassTime",
        }
    )

    includeGeoJSON: bool = Field(
        default=False,
        description="Boolean indicating whether to include associated GeoJSON. Defaults to false.",
    )
    includeGeoJSONSummary: bool = Field(
        default=False,
        description="Boolean indicating whether to include associated GeoJSON summary bounding box. Defaults to false.",
    )
    includeRegion: bool = Field(
        default=False,
        description="Boolean indicating whether to include associated DS9 region. Defaults to false.",
    )
    ignoreCache: bool = Field(
        default=False,
        description="Boolean indicating whether to ignore field caching. Defaults to false.",
    )
    localizationDateobs: str | None = Field(
        default=None,
        description=(
            "Include fields within a given localization. "
            "Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). "
            "Each localization is associated with a specific GCNEvent by "
            "the date the event happened, and this date is used as a unique "
            "identifier. It can be therefore found as Localization.dateobs, "
            "queried from the /api/localization endpoint or dateobs in the "
            "GcnEvent page table."
        ),
    )
    localizationName: str | None = Field(
        default=None,
        description=(
            "Name of localization / skymap to use. "
            "Can be found in Localization.localization_name queried from "
            "/api/localization endpoint or skymap name in GcnEvent page table."
        ),
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include fields. Defaults to 0.95.",
    )
    airmassTime: str | None = Field(
        default=None,
        description=(
            "Time to use for airmass calculation in "
            "ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). "
            "Defaults to localizationDateobs if not supplied."
        ),
    )
    name: str | None = Field(
        default=None,
        description="Filter by name (exact match)",
    )


class InstrumentPostBody(BaseModel):
    """Request body for creating an instrument.

    Pass-through blob fields (sensitivity/configuration/field/reference data)
    are typed permissively; the handler and marshmallow schema enforce the
    real validation rules.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Instrument name.")
    acknowledgment: str | None = Field(
        default=None,
        description="Sentence to cite this instrument with, used to build a "
        "source's acknowledgment block. Falls back to the instrument name when "
        "unset.",
    )
    type: str | None = Field(
        default=None,
        description="Instrument type, one of Imager, Spectrograph, or Imaging "
        "Spectrograph.",
    )
    band: str | None = Field(
        default=None,
        description="The spectral band covered by the instrument (e.g., Optical, IR).",
    )
    telescope_id: int | None = Field(
        default=None,
        description="The ID of the Telescope that hosts the Instrument.",
    )
    filters: list | None = Field(
        default=None,
        description="List of filters on the instrument. If the instrument has no "
        "filters (e.g., because it is a spectrograph), leave blank or pass the "
        "empty list.",
    )
    sensitivity_data: dict[str, Any] | str | None = Field(
        default=None,
        description="List of filters and associated limiting magnitude and exposure "
        "time. Sensitivity_data filters must be a subset of the instrument filters. "
        "Limiting magnitude assumed to be AB magnitude.",
    )
    configuration_data: dict[str, Any] | str | None = Field(
        default=None,
        description="Instrument configuration properties such as instrument overhead, "
        "filter change time, readout, etc.",
    )
    field_data: dict[str, Any] | str | None = Field(
        default=None, description="List of ID, RA, and Dec for each field."
    )
    field_region: str | None = Field(
        default=None,
        description="Serialized version of a regions.Region describing the shape of "
        "the instrument field. Note: should only include field_region or "
        "field_fov_type.",
    )
    references: dict[str, Any] | str | None = Field(
        default=None,
        description="List of filter, and limiting magnitude for each reference.",
    )
    field_fov_type: str | None = Field(
        default=None,
        description="Option for instrument field shape. Must be either circle or "
        "rectangle. Note: should only include field_region or field_fov_type.",
    )
    field_fov_attributes: list | float | str | None = Field(
        default=None,
        description="Option for instrument field shape parameters. Single float "
        "radius in degrees in case of circle or list of two floats (height and "
        "width) in case of a rectangle.",
    )
    api_classname: str | None = Field(
        default=None, description="Name of the instrument's API class."
    )
    api_classname_obsplan: str | None = Field(
        default=None,
        description="Name of the instrument's ObservationPlan API class.",
    )
    listener_classname: str | None = Field(
        default=None, description="Name of the instrument's listener class."
    )
    treasuremap_id: int | None = Field(
        default=None, description="treasuremap.space API ID for this instrument."
    )
    tns_id: int | None = Field(
        default=None, description="TNS API ID for this instrument."
    )
    across_id: str | None = Field(
        default=None, description="NASA ACROSS instrument UUID."
    )
    region: str | None = Field(
        default=None, description="Instrument astropy.regions representation."
    )
    status: dict[str, Any] | None = Field(
        default=None,
        description="JSON describing the latest status of the instrument.",
    )
    last_status_update: str | None = Field(
        default=None, description="The time at which the status was last updated."
    )
    has_fields: bool | None = Field(
        default=None, description="Whether the instrument has fields or not."
    )
    has_region: bool | None = Field(
        default=None, description="Whether the instrument has a region or not."
    )


class InstrumentPutBody(InstrumentPostBody):
    """Request body for updating an instrument (same shape as the post body)."""


class InstrumentPostResponse(BaseModel):
    """Data payload returned when creating an instrument."""

    id: int = Field(description="New instrument ID")


class InstrumentLogPostBody(BaseModel):
    """Request body for posting instrument logs."""

    model_config = ConfigDict(extra="forbid")

    start_date: str = Field(
        description="Arrow-parseable date string (e.g. 2020-01-01)."
    )
    end_date: str = Field(description="Arrow-parseable date string (e.g. 2020-01-01).")
    log: str | dict[str, Any] = Field(
        description="Nested JSON containing the log messages, or a parsable "
        "string of log lines."
    )


class InstrumentLogPostResponse(BaseModel):
    """Data payload returned when posting instrument logs."""

    id: int = Field(description="The id of the InstrumentLog")


class InstrumentStatusPutBody(BaseModel):
    """Request body for updating an instrument's status."""

    model_config = ConfigDict(extra="forbid")

    status: str | dict[str, Any] | None = Field(
        default=None,
        description="The status of the instrument, as a JSON object or a "
        "JSON-encoded string. When empty or omitted, the status is instead "
        "refreshed from the instrument's remote API.",
    )


class InstrumentLogGetQuery(BaseModel):
    """Query parameters for retrieving instrument logs."""

    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). Only return logs ending after this date.",
    )
    endDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). Only return logs starting before this date.",
    )


class InstrumentLogExternalAPIGetQuery(BaseModel):
    """Query parameters for retrieving instrument logs from an external API."""

    model_config = ConfigDict(extra="forbid")

    startDate: str = Field(
        description="Arrow-parseable date string (e.g. 2020-01-01).",
    )
    endDate: str = Field(
        description="Arrow-parseable date string (e.g. 2020-01-01).",
    )


__all__ = [
    "InstrumentGetQuery",
    "InstrumentPostBody",
    "InstrumentPutBody",
    "InstrumentPostResponse",
    "InstrumentLogPostBody",
    "InstrumentLogPostResponse",
    "InstrumentStatusPutBody",
    "InstrumentLogGetQuery",
    "InstrumentLogExternalAPIGetQuery",
    "InstrumentPost",
    "InstrumentPut",
    "InstrumentFieldResponse",
    "InstrumentLogResponse",
    "InstrumentResponse",
]
