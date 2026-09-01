"""Response models for ``/api/photometric_series``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.streams import StreamResponse


class PhotometricSeriesDetailResponse(BaseModel):
    """A photometric series: one light curve of one object in one series."""

    # ``PhotometricSeries.to_dict`` returns the mapper columns plus ``data``
    # (the light curve in the requested ``dataFormat``), ``group_ids``,
    # ``stream_ids``, ``groups`` and ``streams``; the group/stream entries are
    # trimmed to a few columns. ``obj``, ``instrument``, ``owner``,
    # ``followup_request`` and ``assignment`` are lazy-loaded relationships that
    # these endpoints never touch, so they are never returned.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    series_name: str | None = None
    series_obj_id: str | None = None
    filter: str | None = None
    channel: str | None = None
    origin: str | None = None
    filename: str | None = None
    ra: float | None = None
    dec: float | None = None
    ra_unc: float | None = None
    dec_unc: float | None = None
    mjd_first: float | None = None
    mjd_mid: float | None = None
    mjd_last: float | None = None
    mjd_last_detected: float | None = None
    mag_first: float | None = None
    mag_last: float | None = None
    mag_last_detected: float | None = None
    is_detected: bool | None = None
    exp_time: float | None = None
    frame_rate: float | None = None
    num_exp: int | None = None
    time_stamp_alignment: Literal["start", "middle", "end"] | None = None
    limiting_mag: float | None = None
    ref_flux: float | None = None
    ref_fluxerr: float | None = None
    mean_mag: float | None = None
    rms_mag: float | None = None
    robust_mag: float | None = None
    robust_rms: float | None = None
    median_snr: float | None = None
    best_snr: float | None = None
    worst_snr: float | None = None
    medians: dict[str, Any] | None = None
    maxima: dict[str, Any] | None = None
    minima: dict[str, Any] | None = None
    stds: dict[str, Any] | None = None
    altdata: dict[str, Any] | None = None
    hash: str | None = None
    autodelete: bool | None = None
    instrument_id: int | None = None
    followup_request_id: int | None = None
    assignment_id: int | None = None
    owner_id: int | None = None
    group_ids: list[int] = Field(default_factory=list)
    stream_ids: list[int] = Field(default_factory=list)
    groups: list[GroupResponse] = Field(default_factory=list)
    streams: list[StreamResponse] = Field(default_factory=list)
    data: dict[str, list[Any]] | str | None = None


class PhotometricSeriesPageResponse(BaseModel):
    """One page of results from a photometric series query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    series: list[PhotometricSeriesDetailResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)
