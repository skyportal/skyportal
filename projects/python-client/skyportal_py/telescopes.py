"""Typed endpoint functions for ``/api/telescope``."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import EphemerisResponse, TelescopeResponse
from skyportal_py_models.telescopes import (
    TelescopePost,
    TelescopePostResponse,
    TelescopePut,
)

from skyportal_py._http import unwrap

__all__ = [
    "EphemerisResponse",
    "TelescopePost",
    "TelescopePostResponse",
    "TelescopePut",
    "TelescopeResponse",
]


def fetch_telescopes(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    name: str | None = None,
    latitude_min: float | None = None,
    latitude_max: float | None = None,
    longitude_min: float | None = None,
    longitude_max: float | None = None,
) -> list[TelescopeResponse]:
    """Retrieve telescopes, optionally filtered by name or location box.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str, optional
        Exact telescope name to match.
    latitude_min, latitude_max : float, optional
        Keep telescopes whose latitude lies in this range, in degrees.
    longitude_min, longitude_max : float, optional
        Keep telescopes whose longitude lies in this range, in degrees.
    """
    params = {
        "name": name,
        "latitudeMin": latitude_min,
        "latitudeMax": latitude_max,
        "longitudeMin": longitude_min,
        "longitudeMax": longitude_max,
    }
    response = client.get(
        "/api/telescope",
        params={key: value for key, value in params.items() if value is not None},
    )
    return [TelescopeResponse.model_validate(item) for item in unwrap(response)]


def fetch_telescope(client: httpx.Client, telescope_id: int) -> TelescopeResponse:
    """Retrieve a single telescope by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    telescope_id : int
        ID of the telescope.
    """
    response = client.get(f"/api/telescope/{telescope_id}")
    return TelescopeResponse.model_validate(unwrap(response))


def post_telescope(
    client: httpx.Client,
    payload: TelescopePost,
) -> TelescopePostResponse:
    """Create a telescope.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : TelescopePost
        The telescope to create. ``name`` is the unabbreviated facility
        name, ``nickname`` the abbreviated one, and ``diameter`` is in
        meters. ``fixed_location`` defaults to true server-side, in which
        case ``lat``, ``lon``, and ``elevation`` are required.
    """
    response = client.post("/api/telescope", json=payload.model_dump(exclude_none=True))
    return TelescopePostResponse.model_validate(unwrap(response))


def update_telescope(
    client: httpx.Client,
    telescope_id: int,
    payload: TelescopePut,
) -> None:
    """Update a telescope.

    Only the provided fields are sent; omitted fields are left unchanged.
    Requires the "Manage telescopes" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    telescope_id : int
        ID of the telescope to update.
    payload : TelescopePut
        The fields to change.
    """
    unwrap(
        client.put(
            f"/api/telescope/{telescope_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def delete_telescope(client: httpx.Client, telescope_id: int) -> None:
    """Delete a telescope.

    Requires the "Manage telescopes" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    telescope_id : int
        ID of the telescope to delete.
    """
    unwrap(client.delete(f"/api/telescope/{telescope_id}"))
