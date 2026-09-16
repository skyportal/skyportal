"""Response models for ``/api/sources/{obj_id}/scout_ephemeris``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScoutEphemerisRowResponse(BaseModel):
    """One ephemeris row from JPL Scout.

    ``time`` is Scout's raw ``YYYY-MM-DD HH:MM:SS`` string, and the two
    ``*_sigma_limits`` dicts are passed through verbatim, with their
    ``min``/``max`` values still strings.
    """

    model_config = ConfigDict(extra="forbid")

    time: str | None = None
    ra: float
    dec: float
    sigma_pos_arcmin: float | None = None
    vmag: float | None = None
    rate_arcsec_per_min: float | None = None
    position_angle: float | None = None
    ra_sigma_limits: dict[str, str] | None = None
    dec_sigma_limits: dict[str, str] | None = None


class ScoutEphemerisResponse(BaseModel):
    """A Scout ephemeris for an unconfirmed solar-system candidate.

    ``hours`` may come back shorter than requested when the window was
    clamped; ``ephemeris`` is never empty on the success path.
    """

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    tdes: str
    obs_code: str
    step_minutes: int
    hours: float
    count: int
    ephemeris: list[ScoutEphemerisRowResponse] = Field(default_factory=list)


__all__ = [
    "ScoutEphemerisResponse",
    "ScoutEphemerisRowResponse",
]
