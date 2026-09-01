"""Response models for ``/api/telescope``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

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


__all__ = [
    "TelescopePost",
    "TelescopePut",
    "EphemerisResponse",
    "TelescopeResponse",
]
