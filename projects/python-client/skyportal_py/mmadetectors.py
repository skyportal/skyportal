"""Typed endpoint functions for ``/api/mmadetector``."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import MMADetectorResponse
from skyportal_py_models.mmadetectors import (
    MMADetectorPost,
    MMADetectorPostResponse,
    MMADetectorSpectrumPost,
    MMADetectorSpectrumPostResponse,
    MMADetectorSpectrumResponse,
    MMADetectorTimeIntervalResponse,
    MMADetectorTimeIntervalsPostResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "MMADetectorPost",
    "MMADetectorPostResponse",
    "MMADetectorResponse",
    "MMADetectorSpectrumPost",
    "MMADetectorSpectrumPostResponse",
    "MMADetectorSpectrumResponse",
    "MMADetectorTimeIntervalResponse",
    "MMADetectorTimeIntervalsPostResponse",
]


def fetch_mmadetector(client: httpx.Client, mmadetector_id: int) -> MMADetectorResponse:
    """Retrieve a single MMA detector by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    mmadetector_id : int
        ID of the MMA detector.
    """
    response = client.get(f"/api/mmadetector/{mmadetector_id}")
    return MMADetectorResponse.model_validate(unwrap(response))


def fetch_mmadetectors(
    client: httpx.Client,
    *,
    name: str | None = None,
) -> list[MMADetectorResponse]:
    """Retrieve all MMA detectors.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str, optional
        Restrict to detectors whose name contains this string.
    """
    params: dict[str, str] = {}
    if name is not None:
        params["name"] = name
    response = client.get("/api/mmadetector", params=params)
    return [
        MMADetectorResponse.model_validate(detector) for detector in unwrap(response)
    ]


def post_mmadetector(
    client: httpx.Client,
    payload: MMADetectorPost,
) -> MMADetectorPostResponse:
    """Create an MMA detector.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : MMADetectorPost
        The detector to create. If ``fixed_location`` is true, ``lat`` must
        be between -90 and 90 and ``lon`` between -180 and 180.
    """
    response = client.post(
        "/api/mmadetector", json=payload.model_dump(exclude_none=True)
    )
    return MMADetectorPostResponse.model_validate(unwrap(response))


def update_mmadetector(  # noqa: PLR0913 -- mirrors the endpoint's body parameters
    client: httpx.Client,
    mmadetector_id: int,
    *,
    name: str | None = None,
    nickname: str | None = None,
    type: str | None = None,  # noqa: A002 -- mirrors the endpoint's field name
    lat: float | None = None,
    lon: float | None = None,
    fixed_location: bool | None = None,
) -> None:
    """Update fields of an existing MMA detector.

    Only the provided fields are sent; omitted fields are left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    mmadetector_id : int
        ID of the MMA detector to update.
    name, nickname : str, optional
        New unabbreviated and abbreviated facility names.
    type : str, optional
        New detector type, e.g. ``"gravitational wave"``.
    lat, lon : float, optional
        New coordinates, in degrees.
    fixed_location : bool, optional
        Whether the detector has a fixed location.
    """
    fields = {
        "name": name,
        "nickname": nickname,
        "type": type,
        "lat": lat,
        "lon": lon,
        "fixed_location": fixed_location,
    }
    payload = {name_: value for name_, value in fields.items() if value is not None}
    unwrap(client.patch(f"/api/mmadetector/{mmadetector_id}", json=payload))


def delete_mmadetector(client: httpx.Client, mmadetector_id: int) -> None:
    """Delete an MMA detector.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    mmadetector_id : int
        ID of the MMA detector to delete.
    """
    unwrap(client.delete(f"/api/mmadetector/{mmadetector_id}"))


def fetch_mmadetector_spectrum(
    client: httpx.Client,
    spectrum_id: int,
) -> MMADetectorSpectrumResponse:
    """Retrieve a single MMA detector spectrum by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    spectrum_id : int
        ID of the MMA detector spectrum.
    """
    response = client.get(f"/api/mmadetector/spectra/{spectrum_id}")
    return MMADetectorSpectrumResponse.model_validate(unwrap(response))


def fetch_mmadetector_spectra(
    client: httpx.Client,
    *,
    observed_before: str | None = None,
    observed_after: str | None = None,
    detector_ids: list[int] | None = None,
    group_ids: list[int] | None = None,
) -> list[MMADetectorSpectrumResponse]:
    """Query MMA detector spectra.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observed_before, observed_after : str, optional
        Restrict to spectra observed before/after this time, as
        arrow-parseable date strings, e.g. ``"2020-01-01"``.
    detector_ids : list of int, optional
        Restrict to spectra from these MMA detectors.
    group_ids : list of int, optional
        Restrict to spectra saved to these groups.
    """
    params: dict[str, str] = {}
    if observed_before is not None:
        params["observedBefore"] = observed_before
    if observed_after is not None:
        params["observedAfter"] = observed_after
    if detector_ids is not None:
        params["detectorIDs"] = ",".join(str(did) for did in detector_ids)
    if group_ids is not None:
        params["groupIDs"] = ",".join(str(gid) for gid in group_ids)
    response = client.get("/api/mmadetector/spectra", params=params)
    return [
        MMADetectorSpectrumResponse.model_validate(spec) for spec in unwrap(response)
    ]


def post_mmadetector_spectrum(
    client: httpx.Client,
    payload: MMADetectorSpectrumPost,
) -> MMADetectorSpectrumPostResponse:
    """Upload an MMA detector spectrum.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : MMADetectorSpectrumPost
        The spectrum to upload. If ``group_ids`` is omitted, the server
        applies its default visibility; pass ``"all"`` to share with all
        accessible groups.
    """
    response = client.post(
        "/api/mmadetector/spectra", json=payload.model_dump(exclude_none=True)
    )
    return MMADetectorSpectrumPostResponse.model_validate(unwrap(response))


def update_mmadetector_spectrum(
    client: httpx.Client,
    spectrum_id: int,
    payload: MMADetectorSpectrumPost,
) -> None:
    """Update an MMA detector spectrum.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    spectrum_id : int
        ID of the MMA detector spectrum to update.
    payload : MMADetectorSpectrumPost
        The new spectrum data. Groups in ``group_ids`` are added to the
        spectrum's existing groups.
    """
    unwrap(
        client.patch(
            f"/api/mmadetector/spectra/{spectrum_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def delete_mmadetector_spectrum(client: httpx.Client, spectrum_id: int) -> None:
    """Delete an MMA detector spectrum.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    spectrum_id : int
        ID of the MMA detector spectrum to delete.
    """
    unwrap(client.delete(f"/api/mmadetector/spectra/{spectrum_id}"))


def fetch_mmadetector_time_interval(
    client: httpx.Client,
    time_interval_id: int,
) -> MMADetectorTimeIntervalResponse:
    """Retrieve a single MMA detector time interval by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    time_interval_id : int
        ID of the MMA detector time interval.
    """
    response = client.get(f"/api/mmadetector/time_intervals/{time_interval_id}")
    return MMADetectorTimeIntervalResponse.model_validate(unwrap(response))


def fetch_mmadetector_time_intervals(
    client: httpx.Client,
    *,
    observed_before: str | None = None,
    observed_after: str | None = None,
    detector_ids: list[int] | None = None,
    group_ids: list[int] | None = None,
) -> list[MMADetectorTimeIntervalResponse]:
    """Query MMA detector time intervals.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    observed_before, observed_after : str, optional
        Restrict to time intervals observed before/after this time, as
        arrow-parseable date strings, e.g. ``"2020-01-01"``.
    detector_ids : list of int, optional
        Restrict to time intervals from these MMA detectors.
    group_ids : list of int, optional
        Restrict to time intervals saved to these groups.
    """
    params: dict[str, str] = {}
    if observed_before is not None:
        params["observedBefore"] = observed_before
    if observed_after is not None:
        params["observedAfter"] = observed_after
    if detector_ids is not None:
        params["detectorIDs"] = ",".join(str(did) for did in detector_ids)
    if group_ids is not None:
        params["groupIDs"] = ",".join(str(gid) for gid in group_ids)
    response = client.get("/api/mmadetector/time_intervals", params=params)
    return [
        MMADetectorTimeIntervalResponse.model_validate(interval)
        for interval in unwrap(response)
    ]


def post_mmadetector_time_intervals(
    client: httpx.Client,
    detector_id: int,
    time_intervals: list[list[str]],
    *,
    group_ids: list[int] | str | None = None,
) -> MMADetectorTimeIntervalsPostResponse:
    """Upload MMA detector time intervals.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    detector_id : int
        ID of the MMA detector the intervals belong to.
    time_intervals : list of list of str
        The intervals to upload, each a ``[start, end]`` pair of UTC time
        strings.
    group_ids : list of int or str, optional
        Share the intervals with these groups. If omitted, the server
        applies its default visibility; pass ``"all"`` to share with all
        accessible groups.
    """
    payload: dict[str, int | list[list[str]] | list[int] | str] = {
        "detector_id": detector_id,
        "time_intervals": time_intervals,
    }
    if group_ids is not None:
        payload["group_ids"] = group_ids
    response = client.post("/api/mmadetector/time_intervals", json=payload)
    return MMADetectorTimeIntervalsPostResponse.model_validate(unwrap(response))


def update_mmadetector_time_interval(
    client: httpx.Client,
    time_interval_id: int,
    *,
    time_interval: list[str] | None = None,
    group_ids: list[int] | str | None = None,
) -> None:
    """Update an MMA detector time interval.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    time_interval_id : int
        ID of the MMA detector time interval to update.
    time_interval : list of str, optional
        New ``[start, end]`` pair of UTC time strings.
    group_ids : list of int or str, optional
        Groups to add to the interval's visibility; pass ``"all"`` for all
        accessible groups.
    """
    payload: dict[str, list[str] | list[int] | str] = {}
    if time_interval is not None:
        payload["time_interval"] = time_interval
    if group_ids is not None:
        payload["group_ids"] = group_ids
    unwrap(
        client.patch(
            f"/api/mmadetector/time_intervals/{time_interval_id}", json=payload
        )
    )


def delete_mmadetector_time_interval(
    client: httpx.Client,
    time_interval_id: int,
) -> None:
    """Delete an MMA detector time interval.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    time_interval_id : int
        ID of the MMA detector time interval to delete.
    """
    unwrap(client.delete(f"/api/mmadetector/time_intervals/{time_interval_id}"))
