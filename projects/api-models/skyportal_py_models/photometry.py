"""Response models for photometry."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.annotations import AnnotationDetailResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.streams import StreamResponse
from skyportal_py_models.users import UserResponse


class PhotometryValidationResponse(BaseModel):
    """A validated/rejected mark on a photometry point."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    photometry_id: int | None = None
    validated: bool | None = None
    validator_id: int | None = None
    explanation: str | None = None
    notes: str | None = None


class _SerializedPhotometryResponse(BaseModel):
    """A photometry point as built by the ``serialize`` helper."""

    # ``serialize`` never returns ``Photometry.to_dict()``: it hand-builds a
    # dict whose keys depend on the ``format`` query parameter. ``mag``,
    # ``magerr`` and ``limiting_mag`` are only present for ``format="mag"``,
    # ``flux``, ``fluxerr`` and ``zp`` only for ``format="flux"``, and both
    # sets for ``format="both"``. The ``ref_*``/``tot_*``/``mag(ref|tot)``
    # block is only present when the point has a reference flux, and the
    # ``extinction``/``mag_corr``/``flux_corr`` keys only when the caller
    # asked for extinction. ``groups``, ``annotations``, ``owner``,
    # ``streams`` and ``validations`` are each opt-in per endpoint, and the
    # ``owner``/``groups``/``streams`` entries are trimmed to a few columns.

    model_config = ConfigDict(extra="forbid")

    id: int
    obj_id: str | None = None
    ra: float | None = None
    dec: float | None = None
    ra_unc: float | None = None
    dec_unc: float | None = None
    filter: str | None = None
    mjd: float | None = None
    snr: float | None = None
    instrument_id: int | None = None
    instrument_name: str | None = None
    origin: str | None = None
    # The duplicate-resolution upload path can leave the literal string
    # "NaN" in place of a point's altdata dict.
    altdata: dict[str, Any] | str | None = None
    created_at: datetime | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    annotations: list[AnnotationDetailResponse] = Field(default_factory=list)
    owner: UserResponse | None = None
    streams: list[StreamResponse] = Field(default_factory=list)
    validations: list[PhotometryValidationResponse] = Field(default_factory=list)
    magsys: str | None = None
    mag: float | None = None
    magerr: float | None = None
    limiting_mag: float | None = None
    flux: float | None = None
    fluxerr: float | None = None
    zp: float | None = None
    ref_flux: float | None = None
    ref_fluxerr: float | None = None
    tot_flux: float | None = None
    tot_fluxerr: float | None = None
    magref: float | None = None
    magtot: float | None = None
    e_magref: float | None = None
    e_magtot: float | None = None
    extinction: float | None = None
    mag_corr: float | None = None
    flux_corr: float | None = None


class PhotometryPointResponse(_SerializedPhotometryResponse):
    """A single photometry point of a source."""

    # ``GET /api/sources/{obj_id}/photometry`` returns individual photometry
    # points *and* the rows of the object's photometric series in one list, so
    # this model also carries the extra keys a series row has: ``instrument``
    # and ``telescope`` (names, not objects) and, when the caller asked to
    # phase-fold, ``phase``. ``format="plot"`` returns a strict subset.
    #
    # extra="allow" because a series row also carries whatever auxiliary
    # columns the uploaded data file had (PhotometricSeries.data is free-form);
    # forbidding them would reject valid payloads.
    model_config = ConfigDict(extra="allow")

    instrument: str | None = None
    telescope: str | None = None
    phase: float | None = None


class PhotometryRangePointResponse(_SerializedPhotometryResponse):
    """A photometry point as serialized by the date-range query."""


class PhotometryPost(BaseModel):
    """Payload for posting one or many photometry points.

    Provide either ``mag``/``magerr`` (magnitude space) or
    ``flux``/``fluxerr``/``zp`` (flux space). For non-detections, leave the
    measurement fields unset and provide ``limiting_mag``. Every measurement
    field also accepts a 1D list to upload many points at once; scalars are
    broadcast across the lists, and a None entry inside a ``mag``/``flux``
    list marks that point as a non-detection.
    """

    model_config = ConfigDict(extra="forbid")

    obj_id: str | list[str]
    mjd: float | list[float]
    instrument_id: int | list[int]
    filter: str | list[str]
    magsys: str | list[str] = "ab"
    mag: float | list[float | None] | None = None
    magerr: float | list[float | None] | None = None
    limiting_mag: float | list[float | None] | None = None
    limiting_mag_nsigma: float | list[float | None] | None = None
    magref: float | list[float | None] | None = None
    e_magref: float | list[float | None] | None = None
    flux: float | list[float | None] | None = None
    fluxerr: float | list[float | None] | None = None
    zp: float | list[float | None] | None = None
    ref_flux: float | list[float | None] | None = None
    ref_fluxerr: float | list[float | None] | None = None
    ref_zp: float | list[float | None] | None = None
    ra: float | list[float | None] | None = None
    dec: float | list[float | None] | None = None
    ra_unc: float | list[float | None] | None = None
    dec_unc: float | list[float | None] | None = None
    origin: str | list[str | None] | None = None
    assignment_id: int | None = None
    altdata: dict[str, Any] | list[dict[str, Any] | None] | None = None
    extinction_corrected: bool | None = None
    group_ids: list[int] | Literal["all"] | None = None
    stream_ids: list[int] | None = None


class PhotometryUpdate(BaseModel):
    """Payload for updating an existing photometry point.

    Every field is optional: the server loads the point, applies the given
    fields, and re-validates the result as either a flux-space
    (``flux``/``fluxerr``/``zp``) or magnitude-space (``mag``/``magerr``)
    measurement. Only the fields explicitly set on the payload are sent, so
    passing ``None`` explicitly (e.g. ``mag=None, magerr=None`` to turn a
    detection into a non-detection) sends a null, while omitting a field
    leaves it unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = None
    mjd: float | None = None
    instrument_id: int | None = None
    filter: str | None = None
    magsys: str | None = None
    mag: float | None = None
    magerr: float | None = None
    limiting_mag: float | None = None
    magref: float | None = None
    e_magref: float | None = None
    flux: float | None = None
    fluxerr: float | None = None
    zp: float | None = None
    ref_flux: float | None = None
    ref_fluxerr: float | None = None
    ref_zp: float | None = None
    ra: float | None = None
    dec: float | None = None
    ra_unc: float | None = None
    dec_unc: float | None = None
    origin: str | None = None
    alert_id: int | None = None
    assignment_id: int | None = None
    altdata: dict[str, Any] | None = None
    group_ids: list[int] | None = None
    stream_ids: list[int] | None = None
