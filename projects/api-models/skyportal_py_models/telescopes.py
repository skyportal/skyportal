"""Response models for ``/api/telescope``."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import EphemerisResponse, TelescopeResponse


class TelescopePost(BaseModel):
    """Payload for creating a telescope."""

    model_config = ConfigDict(extra="forbid")

    name: str
    nickname: str
    diameter: float
    lat: float | None = None
    lon: float | None = None
    elevation: float | None = None
    skycam_link: str | None = None
    weather_link: str | None = None
    robotic: bool = False
    fixed_location: bool | None = None


class TelescopePut(BaseModel):
    """Payload for updating a telescope."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    nickname: str | None = None
    diameter: float | None = None
    lat: float | None = None
    lon: float | None = None
    elevation: float | None = None
    skycam_link: str | None = None
    weather_link: str | None = None
    robotic: bool | None = None
    fixed_location: bool | None = None


class TelescopePostBody(BaseModel):
    """Request body for creating a telescope."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Unabbreviated facility name (e.g., Palomar 200-inch "
        "Hale Telescope)."
    )
    nickname: str = Field(description="Abbreviated facility name (e.g., P200).")
    diameter: float = Field(description="Diameter in meters.")
    lat: float | None = Field(default=None, description="Latitude in deg.")
    lon: float | None = Field(default=None, description="Longitude in deg.")
    elevation: float | None = Field(default=None, description="Elevation in meters.")
    mpc_obscode: str | None = Field(
        default=None,
        description="Minor Planet Center observatory code, e.g. 'X05' (Rubin) "
        "or 'I41' (ZTF).",
    )
    skycam_link: str | None = Field(
        default=None, description="Link to the telescope's sky camera."
    )
    weather_link: str | None = Field(
        default=None, description="Link to the preferred weather site."
    )
    robotic: bool = Field(default=False, description="Is this telescope robotic?")
    fixed_location: bool | None = Field(
        default=None,
        description="Does this telescope have a fixed location (lon, lat, "
        "elev)? Defaults to true.",
    )
    acknowledgment: str | None = Field(
        default=None,
        description="Sentence papers should cite this telescope with, used to "
        "build a source's acknowledgment block.",
    )


class TelescopePostResponse(BaseModel):
    """Data payload returned when creating a telescope."""

    id: int = Field(description="New telescope ID")


class TelescopePutBody(BaseModel):
    """Request body for updating a telescope."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        description="Unabbreviated facility name (e.g., Palomar 200-inch "
        "Hale Telescope).",
    )
    nickname: str | None = Field(
        default=None, description="Abbreviated facility name (e.g., P200)."
    )
    diameter: float | None = Field(default=None, description="Diameter in meters.")
    lat: float | None = Field(default=None, description="Latitude in deg.")
    lon: float | None = Field(default=None, description="Longitude in deg.")
    elevation: float | None = Field(default=None, description="Elevation in meters.")
    mpc_obscode: str | None = Field(
        default=None,
        description="Minor Planet Center observatory code, e.g. 'X05' (Rubin) "
        "or 'I41' (ZTF).",
    )
    skycam_link: str | None = Field(
        default=None, description="Link to the telescope's sky camera."
    )
    weather_link: str | None = Field(
        default=None, description="Link to the preferred weather site."
    )
    robotic: bool | None = Field(default=None, description="Is this telescope robotic?")
    fixed_location: bool | None = Field(
        default=None,
        description="Does this telescope have a fixed location (lon, lat, elev)?",
    )
    acknowledgment: str | None = Field(
        default=None,
        description="Sentence papers should cite this telescope with, used to "
        "build a source's acknowledgment block.",
    )


class TelescopeGetQuery(BaseModel):
    """Query parameters for retrieving telescopes."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    name: str | None = Field(
        default=None,
        description="Filter by name (exact match)",
    )
    latitudeMin: float | None = Field(
        default=None,
        description="Filter by latitude >= latitudeMin",
    )
    latitudeMax: float | None = Field(
        default=None,
        description="Filter by latitude <= latitudeMax",
    )
    longitudeMin: float | None = Field(
        default=None,
        description="Filter by longitude >= longitudeMin",
    )
    longitudeMax: float | None = Field(
        default=None,
        description="Filter by longitude <= longitudeMax",
    )


__all__ = [
    "TelescopePostBody",
    "TelescopePostResponse",
    "TelescopePutBody",
    "TelescopeGetQuery",
    "TelescopePost",
    "TelescopePut",
    "EphemerisResponse",
    "TelescopeResponse",
]
