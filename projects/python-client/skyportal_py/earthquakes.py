"""Typed endpoint functions for ``/api/earthquake``."""

from __future__ import annotations

import httpx
from skyportal_py_models.earthquakes import (
    EarthquakeMeasurementResponse,
    EarthquakeNoticeResponse,
    EarthquakePost,
    EarthquakePostResponse,
    EarthquakePredictionResponse,
    EarthquakeResponse,
    EarthquakesPageResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "EarthquakeMeasurementResponse",
    "EarthquakeNoticeResponse",
    "EarthquakePost",
    "EarthquakePostResponse",
    "EarthquakePredictionResponse",
    "EarthquakeResponse",
    "EarthquakesPageResponse",
]


def fetch_earthquake(client: httpx.Client, event_id: str) -> EarthquakeResponse:
    """Retrieve a single earthquake event by its event ID.

    The response includes the event's notices (with raw QuakeML content),
    predictions and comments, each sorted newest first.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    event_id : str
        EarthquakeResponse event ID, e.g. ``"us7000abcd"``.
    """
    response = client.get(f"/api/earthquake/{event_id}")
    return EarthquakeResponse.model_validate(unwrap(response))


def fetch_earthquakes(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    status_keep: str | None = None,
    status_remove: str | None = None,
    page_number: int = 1,
    num_per_page: int = 100,
) -> EarthquakesPageResponse:
    """Query earthquake events, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    start_date, end_date : str, optional
        Arrow-parseable date strings (e.g. ``"2020-01-01"``) filtering on the
        date of the event's notices.
    status_keep : str, optional
        Keep only events whose status contains this string.
    status_remove : str, optional
        Drop events whose status contains this string.
    page_number, num_per_page : int, optional
        Pagination controls; the server defaults to page 1 and 100 per page.
    """
    params: dict[str, str | int] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    if status_keep is not None:
        params["statusKeep"] = status_keep
    if status_remove is not None:
        params["statusRemove"] = status_remove
    response = client.get("/api/earthquake", params=params)
    return EarthquakesPageResponse.model_validate(unwrap(response))


def fetch_earthquake_statuses(client: httpx.Client) -> list[str]:
    """Retrieve the distinct status tags used by earthquake events.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/earthquake/status")
    return list(unwrap(response))


def post_earthquake(
    client: httpx.Client,
    payload: EarthquakePost,
) -> EarthquakePostResponse:
    """Ingest an earthquake event.

    Provide either ``xml`` (raw QuakeML) or all of ``date``, ``event_id``,
    ``latitude``, ``longitude``, ``depth`` and ``magnitude``. Posting again
    for a known event adds another notice; only the original poster may
    update an existing event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : EarthquakePost
        The earthquake to ingest.
    """
    response = client.post(
        "/api/earthquake",
        json=payload.model_dump(exclude_none=True),
    )
    return EarthquakePostResponse.model_validate(unwrap(response))


def delete_earthquake(client: httpx.Client, event_id: str) -> None:
    """Delete an earthquake event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    event_id : str
        EarthquakeResponse event ID to delete.
    """
    unwrap(client.delete(f"/api/earthquake/{event_id}"))


def post_earthquake_prediction(
    client: httpx.Client,
    event_id: str,
    mmadetector_id: int,
) -> None:
    """Run and store a seismic arrival prediction for one detector.

    The prediction uses the event's most recent notice, so the event must
    already have one, and the detector must be at a fixed location.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    event_id : str
        EarthquakeResponse event ID.
    mmadetector_id : int
        ID of the MMA detector to predict arrivals for.
    """
    unwrap(
        client.post(
            f"/api/earthquake/{event_id}/mmadetector/{mmadetector_id}/predictions"
        )
    )


def fetch_earthquake_measurement(
    client: httpx.Client,
    event_id: str,
    mmadetector_id: int,
) -> EarthquakeMeasurementResponse:
    """Retrieve the ground velocity measurement for one detector.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    event_id : str
        EarthquakeResponse event ID.
    mmadetector_id : int
        ID of the MMA detector the measurement belongs to.
    """
    response = client.get(
        f"/api/earthquake/{event_id}/mmadetector/{mmadetector_id}/measurements"
    )
    return EarthquakeMeasurementResponse.model_validate(unwrap(response))


def post_earthquake_measurement(
    client: httpx.Client,
    event_id: str,
    mmadetector_id: int,
    *,
    rfamp: float | None = None,
    lockloss: int | None = None,
) -> None:
    """Post a ground velocity measurement for one detector.

    At least one of ``rfamp`` or ``lockloss`` is required. Only one
    measurement may exist per earthquake and detector; use
    :func:`update_earthquake_measurement` to change an existing one.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    event_id : str
        EarthquakeResponse event ID.
    mmadetector_id : int
        ID of the MMA detector the measurement belongs to.
    rfamp : float, optional
        Measured earthquake amplitude, in m/s.
    lockloss : int, optional
        Measured lockloss: 0 (no lockloss) or 1 (lockloss).
    """
    fields = {"rfamp": rfamp, "lockloss": lockloss}
    payload = {name: value for name, value in fields.items() if value is not None}
    unwrap(
        client.post(
            f"/api/earthquake/{event_id}/mmadetector/{mmadetector_id}/measurements",
            json=payload,
        )
    )


def update_earthquake_measurement(
    client: httpx.Client,
    event_id: str,
    mmadetector_id: int,
    *,
    rfamp: float | None = None,
    lockloss: int | None = None,
) -> None:
    """Update the ground velocity measurement for one detector.

    At least one of ``rfamp`` or ``lockloss`` is required; omitted fields are
    left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    event_id : str
        EarthquakeResponse event ID.
    mmadetector_id : int
        ID of the MMA detector the measurement belongs to.
    rfamp : float, optional
        New measured earthquake amplitude, in m/s.
    lockloss : int, optional
        New measured lockloss: 0 (no lockloss) or 1 (lockloss).
    """
    fields = {"rfamp": rfamp, "lockloss": lockloss}
    payload = {name: value for name, value in fields.items() if value is not None}
    unwrap(
        client.patch(
            f"/api/earthquake/{event_id}/mmadetector/{mmadetector_id}/measurements",
            json=payload,
        )
    )


def delete_earthquake_measurement(
    client: httpx.Client,
    event_id: str,
    mmadetector_id: int,
) -> None:
    """Delete the ground velocity measurement for one detector.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    event_id : str
        EarthquakeResponse event ID.
    mmadetector_id : int
        ID of the MMA detector the measurement belongs to.
    """
    unwrap(
        client.delete(
            f"/api/earthquake/{event_id}/mmadetector/{mmadetector_id}/measurements"
        )
    )
