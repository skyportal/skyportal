"""Typed endpoint functions for ``/api/localization``."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import (
    LocalizationCenterResponse,
    LocalizationPropertyResponse,
    LocalizationResponse,
    LocalizationTagResponse,
)

from skyportal_py._http import unwrap, unwrap_content

__all__ = [
    "LocalizationCenterResponse",
    "LocalizationPropertyResponse",
    "LocalizationResponse",
    "LocalizationTagResponse",
]


def fetch_localization(
    client: httpx.Client,
    dateobs: str,
    localization_name: str,
    *,
    include_2d_map: bool = False,
) -> LocalizationResponse:
    """Retrieve a GCN localization by event time and name.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the GCN event, e.g. ``"2023-05-23T12:00:00"``.
    localization_name : str
        Name of the localization, e.g. ``"bayestar.fits.gz"``.
    include_2d_map : bool, optional
        Include the flattened 2D skymap (``flat_2d``) in the response.
        Defaults to false server-side.
    """
    response = client.get(
        f"/api/localization/{dateobs}/name/{localization_name}",
        params={"include2DMap": include_2d_map},
    )
    return LocalizationResponse.model_validate(unwrap(response))


def delete_localization(
    client: httpx.Client,
    dateobs: str,
    localization_name: str,
) -> None:
    """Delete a GCN localization.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the GCN event.
    localization_name : str
        Name of the localization to delete.
    """
    unwrap(client.delete(f"/api/localization/{dateobs}/name/{localization_name}"))


def post_localization_from_notice(
    client: httpx.Client,
    dateobs: str,
    notice_id: int,
) -> None:
    """Ingest the skymap referenced by an existing GCN notice.

    The server reads the stored notice content and posts the skymap it
    references as a new localization. Fails with a conflict if that
    localization already exists, or 404 if the notice has no available
    skymap (e.g. a retraction).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the GCN event the notice belongs to.
    notice_id : int
        ID of the GCN notice to ingest the skymap from.
    """
    unwrap(client.post(f"/api/localization/{dateobs}/notice/{notice_id}"))


def fetch_localization_skymap(
    client: httpx.Client,
    dateobs: str,
    localization_name: str,
) -> bytes:
    """Download a localization's skymap as a FITS file.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    dateobs : str
        UTC event timestamp of the GCN event.
    localization_name : str
        Name of the localization to download.
    """
    response = client.get(
        f"/api/localization/{dateobs}/name/{localization_name}/download"
    )
    return unwrap_content(response)


def fetch_localization_tags(client: httpx.Client) -> list[str]:
    """Retrieve all distinct localization tags.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/localization/tags")
    return [str(tag) for tag in unwrap(response)]


def fetch_localization_properties(client: httpx.Client) -> list[str]:
    """Retrieve all distinct localization property names, sorted.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/localization/properties")
    return [str(name) for name in unwrap(response)]


def fetch_localization_crossmatch(
    client: httpx.Client,
    id1: int,
    id2: int,
) -> bytes:
    """Crossmatch two localizations, returning the intersection as FITS.

    The server multiplies the two flattened skymaps, renormalizes, and
    returns the product as a multi-order FITS skymap.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    id1, id2 : int
        IDs of the two localizations to crossmatch.
    """
    response = client.get(
        "/api/localizationcrossmatch",
        params={"id1": id1, "id2": id2},
    )
    return unwrap_content(response)


def fetch_localization_observability_plot(
    client: httpx.Client,
    localization_id: int,
    *,
    max_airmass: float | None = None,
    twilight: str | None = None,
) -> bytes:
    """Download an observability summary plot (PDF) for a localization.

    Charts when each fixed-location telescope can observe the
    localization's contour center over the day after the event.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    localization_id : int
        ID of the localization to plot observability for.
    max_airmass : float, optional
        Maximum airmass to consider. Server default is 2.5.
    twilight : str, optional
        Twilight definition: ``"astronomical"`` (-18 deg, server
        default), ``"nautical"`` (-12 deg), or ``"civil"`` (-6 deg).
    """
    params: dict[str, float | str] = {}
    if max_airmass is not None:
        params["maxAirmass"] = max_airmass
    if twilight is not None:
        params["twilight"] = twilight
    response = client.get(
        f"/api/localization/{localization_id}/observability",
        params=params,
    )
    return unwrap_content(response)


def fetch_localization_airmass_chart(
    client: httpx.Client,
    localization_id: int,
    telescope_id: int,
) -> bytes:
    """Download an airmass chart (PDF) for a localization at a telescope.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    localization_id : int
        ID of the localization to chart.
    telescope_id : int
        ID of the telescope to compute the airmass for.
    """
    response = client.get(f"/api/localization/{localization_id}/airmass/{telescope_id}")
    return unwrap_content(response)


def fetch_localization_worldmap_plot(
    client: httpx.Client,
    localization_id: int,
    *,
    max_airmass: float | None = None,
    twilight: str | None = None,
) -> bytes:
    """Download a world map plot (PDF) of telescope observability.

    Shows every fixed-location telescope on a world map, colored by the
    probability of the localization region it can observe at event time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    localization_id : int
        ID of the localization to generate the map for.
    max_airmass : float, optional
        Maximum airmass to consider. Server default is 2.5.
    twilight : str, optional
        Twilight definition: ``"astronomical"`` (-18 deg, server
        default), ``"nautical"`` (-12 deg), or ``"civil"`` (-6 deg).
    """
    params: dict[str, float | str] = {}
    if max_airmass is not None:
        params["maxAirmass"] = max_airmass
    if twilight is not None:
        params["twilight"] = twilight
    response = client.get(
        f"/api/localization/{localization_id}/worldmap",
        params=params,
    )
    return unwrap_content(response)
