"""Typed endpoint functions for ``/api/instrument``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models._cyclic import InstrumentFieldResponse, InstrumentResponse
from skyportal_py_models.instruments import (
    InstrumentLogPostResponse,
    InstrumentLogResponse,
    InstrumentPost,
    InstrumentPostResponse,
    InstrumentPut,
)

from skyportal_py._http import unwrap

__all__ = [
    "InstrumentFieldResponse",
    "InstrumentLogPostResponse",
    "InstrumentLogResponse",
    "InstrumentPost",
    "InstrumentPostResponse",
    "InstrumentPut",
    "InstrumentResponse",
]


def fetch_instruments(
    client: httpx.Client,
    *,
    name: str | None = None,
) -> list[InstrumentResponse]:
    """Retrieve instruments, optionally filtered by exact name.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str, optional
        Exact instrument name to match.
    """
    params = {} if name is None else {"name": name}
    response = client.get("/api/instrument", params=params)
    return [InstrumentResponse.model_validate(item) for item in unwrap(response)]


def fetch_instrument(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    instrument_id: int,
    *,
    include_geojson: bool = False,
    include_geojson_summary: bool = False,
    include_region: bool = False,
    ignore_cache: bool = False,
    localization_dateobs: str | None = None,
    localization_name: str | None = None,
    localization_cumprob: float | None = None,
    airmass_time: str | None = None,
) -> InstrumentResponse:
    """Retrieve a single instrument by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument.
    include_geojson : bool, optional
        Include each field's GeoJSON contour in ``fields[].contour``.
    include_geojson_summary : bool, optional
        Include each field's summary contour in ``fields[].contour_summary``.
    include_region : bool, optional
        Include the instrument's ds9 region string in ``region``.
    ignore_cache : bool, optional
        Recompute the localization's field overlap instead of using the
        server's cached field list.
    localization_dateobs : str, optional
        Restrict the returned ``fields`` to those overlapping the
        localization of the GCN event with this ``dateobs``, in ISO 8601
        format (``YYYY-MM-DDTHH:MM:SS.sss``).
    localization_name : str, optional
        Name of the localization / skymap to use. Defaults to the event's
        most recent localization.
    localization_cumprob : float, optional
        Cumulative probability up to which to include fields. Server
        default is 0.95.
    airmass_time : str, optional
        Time to use for each field's airmass calculation, in ISO 8601
        format. Defaults to ``localization_dateobs``.
    """
    params: dict[str, str | float | bool] = {
        "includeGeoJSON": include_geojson,
        "includeGeoJSONSummary": include_geojson_summary,
        "includeRegion": include_region,
        "ignoreCache": ignore_cache,
    }
    if localization_dateobs is not None:
        params["localizationDateobs"] = localization_dateobs
    if localization_name is not None:
        params["localizationName"] = localization_name
    if localization_cumprob is not None:
        params["localizationCumprob"] = localization_cumprob
    if airmass_time is not None:
        params["airmassTime"] = airmass_time
    response = client.get(f"/api/instrument/{instrument_id}", params=params)
    return InstrumentResponse.model_validate(unwrap(response))


def post_instrument(
    client: httpx.Client,
    payload: InstrumentPost,
) -> InstrumentPostResponse:
    """Create an instrument.

    ``type`` must be one of ``"imager"``, ``"spectrograph"``, or
    ``"imaging spectrograph"``, and the instrument name must be unique for
    the telescope. ``sensitivity_data`` and ``configuration_data`` are keyed
    by filter name, and ``sensitivity_data`` filters must be a subset of
    ``filters``. Supply at most one of ``field_region`` (a serialized ds9
    region) or ``field_fov_type`` (``"circle"`` or ``"rectangle"``, which
    requires ``field_fov_attributes``: a radius, or a width and a height, in
    degrees). ``field_data`` maps ``ID``, ``RA``, and ``Dec`` to per-field
    lists and requires one of the two region options; the fields themselves
    are generated asynchronously after the response is returned.
    ``references`` maps ``field`` and ``filter`` (and optionally ``limmag``)
    to per-reference lists.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : InstrumentPost
        The instrument to create.
    """
    response = client.post(
        "/api/instrument", json=payload.model_dump(exclude_none=True)
    )
    return InstrumentPostResponse.model_validate(unwrap(response))


def update_instrument(
    client: httpx.Client,
    instrument_id: int,
    payload: InstrumentPut,
) -> None:
    """Update an instrument.

    Only the provided fields are sent; omitted fields are left unchanged.
    Requires the "Manage instruments" permission. A filter cannot be removed
    while photometry taken in it still references the instrument. Passing
    ``field_data`` regenerates the instrument's fields asynchronously, using
    ``field_region``/``field_fov_type`` if given and otherwise the
    instrument's existing region.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument to update.
    payload : InstrumentPut
        The fields to change.
    """
    unwrap(
        client.put(
            f"/api/instrument/{instrument_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def delete_instrument(client: httpx.Client, instrument_id: int) -> None:
    """Delete an instrument.

    Requires the "Manage instruments" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument to delete.
    """
    unwrap(client.delete(f"/api/instrument/{instrument_id}"))


def delete_instrument_fields(client: httpx.Client, instrument_id: int) -> None:
    """Delete every field associated with an instrument.

    The instrument itself is kept; only its fields are removed and its
    ``has_fields`` flag is updated. Requires the "Manage instruments"
    permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument whose fields to delete.
    """
    unwrap(client.delete(f"/api/instrument/{instrument_id}/fields"))


def fetch_instrument_logs(
    client: httpx.Client,
    instrument_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[InstrumentLogResponse]:
    """Retrieve the logs uploaded for an instrument.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument.
    start_date : str, optional
        Arrow-parseable date string; keep logs ending at or after this time.
    end_date : str, optional
        Arrow-parseable date string; keep logs starting at or before this
        time.
    """
    params: dict[str, str] = {}
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    response = client.get(f"/api/instrument/{instrument_id}/log", params=params)
    return [InstrumentLogResponse.model_validate(item) for item in unwrap(response)]


def post_instrument_log(
    client: httpx.Client,
    instrument_id: int,
    start_date: str,
    end_date: str,
    log: dict[str, Any] | str,
) -> InstrumentLogPostResponse:
    """Upload log messages for an instrument.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument the log belongs to.
    start_date : str
        Arrow-parseable date string for the start of the log period.
    end_date : str
        Arrow-parseable date string for the end of the log period.
    log : dict or str
        The log messages as nested JSON, or as a parseable string of log
        lines that the server converts to JSON.
    """
    payload: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "log": log,
    }
    response = client.post(f"/api/instrument/{instrument_id}/log", json=payload)
    return InstrumentLogPostResponse.model_validate(unwrap(response))


def fetch_instrument_log_external_api(
    client: httpx.Client,
    allocation_id: int,
    *,
    start_date: str,
    end_date: str,
) -> None:
    """Pull instrument logs from an allocation's remote instrument API.

    The retrieved logs are stored server-side rather than returned. Despite
    living under the instrument path, the path ID is an allocation ID. The
    allocation's instrument must define an API class implementing
    ``retrieve_log``. Requires the "Upload data" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation to retrieve logs for.
    start_date : str
        Arrow-parseable date string for the start of the log period.
    end_date : str
        Arrow-parseable date string for the end of the log period.
    """
    params = {"startDate": start_date, "endDate": end_date}
    unwrap(
        client.get(
            f"/api/instrument/{allocation_id}/external_api",
            params=params,
        )
    )


def update_instrument_status(
    client: httpx.Client,
    instrument_id: int,
    *,
    status: dict[str, Any] | None = None,
) -> None:
    """Update an instrument's status.

    When ``status`` is omitted or empty, the status is instead refreshed
    from the instrument's remote API, which requires an allocation whose
    ``altdata`` holds ``ssh_host``, ``ssh_username``, and ``ssh_password``.
    Either way the instrument must define an API class implementing
    ``update_status``. Requires the "Upload data" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument to update.
    status : dict, optional
        The new status. Keys with empty values are dropped server-side.
    """
    payload: dict[str, Any] = {}
    if status is not None:
        payload["status"] = status
    unwrap(client.put(f"/api/instrument/{instrument_id}/status", json=payload))
