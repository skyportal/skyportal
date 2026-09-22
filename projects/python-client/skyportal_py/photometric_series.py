"""Typed endpoint functions for ``/api/photometric_series``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models.photometric_series import (
    PhotometricSeriesPageResponse,
    PhotometricSeriesPost,
    PhotometricSeriesResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "PhotometricSeriesPageResponse",
    "PhotometricSeriesPost",
    "PhotometricSeriesResponse",
    "PhotometricSeriesResponse",
]


def fetch_photometric_series(
    client: httpx.Client,
    photometric_series_id: int,
    *,
    data_format: str = "json",
) -> PhotometricSeriesResponse:
    """Retrieve a single photometric series by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    photometric_series_id : int
        ID of the photometric series.
    data_format : str, optional
        How to return the light curve in the ``data`` field: ``"json"``
        (the default; a mapping of column name to list of values),
        ``"hdf5"`` (a base64-encoded HDF5 bytestream) or ``"none"``
        (omit the data and return metadata only).
    """
    response = client.get(
        f"/api/photometric_series/{photometric_series_id}",
        params={"dataFormat": data_format},
    )
    return PhotometricSeriesResponse.model_validate(unwrap(response))


def fetch_photometric_series_page(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    data_format: str = "none",
    page_number: int = 1,
    num_per_page: int = 100,
    sort_by: str = "obj_id",
    sort_order: str = "asc",
    ra: float | None = None,
    dec: float | None = None,
    radius: float | None = None,
    object_id: str | None = None,
    rejected_object_id: str | None = None,
    series_name: str | None = None,
    series_obj_id: str | None = None,
    filter: str | None = None,  # noqa: A002 -- mirrors the endpoint's query parameter
    channel: str | None = None,
    origin: str | None = None,
    filename: str | None = None,
    start_before: str | None = None,
    start_after: str | None = None,
    mid_before: str | None = None,
    mid_after: str | None = None,
    end_before: str | None = None,
    end_after: str | None = None,
    detected: bool | None = None,
    exp_time: float | None = None,
    min_exp_time: float | None = None,
    max_exp_time: float | None = None,
    min_frame_rate: float | None = None,
    max_frame_rate: float | None = None,
    min_num_exposures: int | None = None,
    max_num_exposures: int | None = None,
    instrument_id: int | None = None,
    followup_request_id: int | None = None,
    assignment_id: int | None = None,
    owner_id: int | None = None,
    mag_brighter_than: float | None = None,
    mag_fainter_than: float | None = None,
    limiting_mag_brighter_than: float | None = None,
    limiting_mag_fainter_than: float | None = None,
    limiting_mag_is_nan: bool | None = None,
    magref_brighter_than: float | None = None,
    magref_fainter_than: float | None = None,
    min_rms: float | None = None,
    max_rms: float | None = None,
    use_robust_mag_and_rms: bool | None = None,
    min_median_snr: float | None = None,
    max_median_snr: float | None = None,
    min_best_snr: float | None = None,
    max_best_snr: float | None = None,
    min_worst_snr: float | None = None,
    max_worst_snr: float | None = None,
    file_hash: str | None = None,
) -> PhotometricSeriesPageResponse:
    """Retrieve one page of photometric series matching a query.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    data_format : str, optional
        How to return each light curve in the ``data`` field: ``"none"``
        (the default for multi-series queries; metadata only), ``"json"`` or
        ``"hdf5"``. Requesting the data can return a very large payload
        unless the query is narrowed down.
    page_number : int, optional
        Page of results to return.
    num_per_page : int, optional
        Results per page. Capped server-side at 500.
    sort_by : str, optional
        Column to sort by, e.g. ``"id"``, ``"ra"``, ``"dec"`` or
        ``"saved_at"``.
    sort_order : str, optional
        ``"asc"`` or ``"desc"``.
    ra : float, optional
        Right ascension in degrees for a cone search. Only applied when
        ``dec`` and ``radius`` are given too.
    dec : float, optional
        Declination in degrees for a cone search.
    radius : float, optional
        Cone search radius in degrees.
    object_id : str, optional
        Substring of the SkyPortal object ID to match.
    rejected_object_id : str, optional
        Comma-separated object IDs to exclude from the results.
    series_name : str, optional
        Exact series name to match.
    series_obj_id : str, optional
        Exact object ID used inside the series, e.g. a TESS TIC ID. This is
        not the SkyPortal object ID.
    filter : str, optional
        Bandpass to match, e.g. ``"ztfg"``.
    channel : str, optional
        Channel name or ID to match.
    origin : str, optional
        Provenance string to match, e.g. the pipeline that produced the data.
    filename : str, optional
        Filename to match. Relative paths are resolved against the server's
        photometric series data directory.
    start_before : str, optional
        Arrow-parseable date; keep only series that started before it.
    start_after : str, optional
        Arrow-parseable date; keep only series that started after it.
    mid_before : str, optional
        Arrow-parseable date; keep only series whose midpoint is before it.
    mid_after : str, optional
        Arrow-parseable date; keep only series whose midpoint is after it.
    end_before : str, optional
        Arrow-parseable date; keep only series that ended before it.
    end_after : str, optional
        Arrow-parseable date; keep only series that ended after it.
    detected : bool, optional
        Keep only series with (``True``) or without (``False``) detections.
    exp_time : float, optional
        Keep only series with exactly this exposure time, in seconds.
    min_exp_time : float, optional
        Minimum exposure time, in seconds.
    max_exp_time : float, optional
        Maximum exposure time, in seconds.
    min_frame_rate : float, optional
        Minimum frame rate, in Hz.
    max_frame_rate : float, optional
        Maximum frame rate, in Hz.
    min_num_exposures : int, optional
        Minimum number of exposures.
    max_num_exposures : int, optional
        Maximum number of exposures.
    instrument_id : int, optional
        Keep only series taken with this instrument.
    followup_request_id : int, optional
        Keep only series taken for this follow-up request.
    assignment_id : int, optional
        Keep only series taken for this observing run assignment.
    owner_id : int, optional
        Keep only series uploaded by this user.
    mag_brighter_than : float, optional
        Keep only series with a mean magnitude at least this bright.
    mag_fainter_than : float, optional
        Keep only series with a mean magnitude at least this faint.
    limiting_mag_brighter_than : float, optional
        Keep only series with a limiting magnitude at least this bright.
    limiting_mag_fainter_than : float, optional
        Keep only series with a limiting magnitude at least this faint.
    limiting_mag_is_nan : bool, optional
        Keep only series that have no limiting magnitude. Only sent when
        true, because the server treats any value it receives as enabled.
    magref_brighter_than : float, optional
        Keep only series that have a magref at least this bright.
    magref_fainter_than : float, optional
        Keep only series that have a magref at least this faint.
    min_rms : float, optional
        Minimum magnitude RMS.
    max_rms : float, optional
        Maximum magnitude RMS.
    use_robust_mag_and_rms : bool, optional
        FilterResponse on ``robust_mag``/``robust_rms`` instead of
        ``mean_mag``/``rms_mag``. Does not affect the magref filters. Only
        sent when true, because the server treats any value it receives as
        enabled.
    min_median_snr : float, optional
        Minimum median signal-to-noise ratio.
    max_median_snr : float, optional
        Maximum median signal-to-noise ratio.
    min_best_snr : float, optional
        Minimum best signal-to-noise ratio.
    max_best_snr : float, optional
        Maximum best signal-to-noise ratio.
    min_worst_snr : float, optional
        Minimum worst signal-to-noise ratio.
    max_worst_snr : float, optional
        Maximum worst signal-to-noise ratio.
    file_hash : str, optional
        MD5 hash of the series data file, useful to match a downloaded HDF5
        file back to its series.
    """
    params: dict[str, Any] = {
        "dataFormat": data_format,
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    optional = {
        "ra": ra,
        "dec": dec,
        "radius": radius,
        "objectID": object_id,
        "rejectedObjectID": rejected_object_id,
        "seriesName": series_name,
        "seriesObjID": series_obj_id,
        "filter": filter,
        "channel": channel,
        "origin": origin,
        "filename": filename,
        "startBefore": start_before,
        "startAfter": start_after,
        "midBefore": mid_before,
        "midAfter": mid_after,
        "endBefore": end_before,
        "endAfter": end_after,
        "detected": detected,
        "expTime": exp_time,
        "minExpTime": min_exp_time,
        "maxExpTime": max_exp_time,
        "minFrameRate": min_frame_rate,
        "maxFrameRate": max_frame_rate,
        "minNumExposures": min_num_exposures,
        "maxNumExposures": max_num_exposures,
        "instrumentID": instrument_id,
        "followupRequestID": followup_request_id,
        "assignmentID": assignment_id,
        "ownerID": owner_id,
        "magBrighterThan": mag_brighter_than,
        "magFainterThan": mag_fainter_than,
        "limitingMagBrighterThan": limiting_mag_brighter_than,
        "limitingMagFainterThan": limiting_mag_fainter_than,
        "limitingMagIsNaN": limiting_mag_is_nan or None,
        "magrefBrighterThan": magref_brighter_than,
        "magrefFainterThan": magref_fainter_than,
        "minRMS": min_rms,
        "maxRMS": max_rms,
        "useRobustMagAndRMS": use_robust_mag_and_rms or None,
        "minMedianSNR": min_median_snr,
        "maxMedianSNR": max_median_snr,
        "minBestSNR": min_best_snr,
        "maxBestSNR": max_best_snr,
        "minWorstSNR": min_worst_snr,
        "maxWorstSNR": max_worst_snr,
        "hash": file_hash,
    }
    params.update({key: value for key, value in optional.items() if value is not None})
    response = client.get("/api/photometric_series", params=params)
    return PhotometricSeriesPageResponse.model_validate(unwrap(response))


def post_photometric_series(
    client: httpx.Client,
    payload: PhotometricSeriesPost,
) -> PhotometricSeriesResponse:
    """Upload a photometric series.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : PhotometricSeriesPost
        The series to upload. ``series_name``, ``series_obj_id``, ``obj_id``
        and ``instrument_id`` are required by the server. If ``group_ids``
        is omitted the series is shared with the configured default group;
        pass ``"all"`` to share it with the public group. The uploader's
        single-user group is always added.
    """
    response = client.post(
        "/api/photometric_series", json=payload.model_dump(exclude_none=True)
    )
    return PhotometricSeriesResponse.model_validate(unwrap(response))


def update_photometric_series(
    client: httpx.Client,
    photometric_series_id: int,
    payload: PhotometricSeriesPost,
) -> PhotometricSeriesResponse:
    """Update a photometric series.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    photometric_series_id : int
        ID of the photometric series to update.
    payload : PhotometricSeriesPost
        Fields to apply; all of them are optional for an update. The series
        is reloaded, its metadata and data updated, and it is written back
        to disk. If new ``data`` is supplied, ``ra``, ``dec``, ``exp_time``
        and ``filter`` are re-inferred from the data columns and override the
        stored values unless they are given explicitly here.
    """
    response = client.patch(
        f"/api/photometric_series/{photometric_series_id}",
        json=payload.model_dump(exclude_none=True),
    )
    return PhotometricSeriesResponse.model_validate(unwrap(response))


def delete_photometric_series(
    client: httpx.Client,
    photometric_series_id: int,
) -> None:
    """Delete a photometric series.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    photometric_series_id : int
        ID of the photometric series to delete. If the series was stored
        with ``autodelete`` enabled, its data file is removed from disk too.
    """
    unwrap(client.delete(f"/api/photometric_series/{photometric_series_id}"))
