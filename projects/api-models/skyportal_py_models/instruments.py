"""Response models for ``/api/instrument``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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


__all__ = [
    "InstrumentPost",
    "InstrumentPut",
    "InstrumentFieldResponse",
    "InstrumentLogResponse",
    "InstrumentResponse",
]
