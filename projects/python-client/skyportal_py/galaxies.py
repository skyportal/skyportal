"""Typed endpoint functions for ``/api/galaxy_catalog``."""

from __future__ import annotations

import httpx
from skyportal_py_models.candidates import GalaxyResponse
from skyportal_py_models.galaxies import (
    GalaxiesPageResponse,
    GalaxyCatalogASCIIPost,
    GalaxyCatalogCountResponse,
    GalaxyCatalogPost,
)

from skyportal_py._http import unwrap

__all__ = [
    "GalaxiesPageResponse",
    "GalaxyCatalogASCIIPost",
    "GalaxyCatalogCountResponse",
    "GalaxyCatalogPost",
    "GalaxyResponse",
]


def fetch_galaxies(  # noqa: PLR0913, PLR0912 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    catalog_name: str | None = None,
    galaxy_name: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    radius: float | None = None,
    min_redshift: float | None = None,
    max_redshift: float | None = None,
    min_distance: float | None = None,
    max_distance: float | None = None,
    min_mstar: float | None = None,
    max_mstar: float | None = None,
    localization_dateobs: str | None = None,
    localization_name: str | None = None,
    localization_cumprob: float | None = None,
    include_geojson: bool = False,
    return_probability: bool = False,
    sort_by: str | None = None,
    sort_order: str | None = None,
    page_number: int = 1,
    num_per_page: int = 1000,
) -> GalaxiesPageResponse:
    """Query galaxies from the galaxy catalogs, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    catalog_name : str, optional
        Restrict to this catalog (exact name match).
    galaxy_name : str, optional
        Restrict to galaxies whose name contains this string.
    ra, dec, radius : float, optional
        Cone-search filter, all in degrees; provide all three together.
    min_redshift, max_redshift : float, optional
        Redshift range filter.
    min_distance, max_distance : float, optional
        Distance range filter, in Mpc.
    min_mstar, max_mstar : float, optional
        Stellar-mass range filter.
    localization_dateobs : str, optional
        Restrict to galaxies inside the localization of the GCN event at
        this time, ISO 8601 format (``YYYY-MM-DDTHH:MM:SS.sss``).
    localization_name : str, optional
        Name of the localization / skymap to use.
    localization_cumprob : float, optional
        Cumulative probability up to which to include galaxies. Server
        default is 0.95.
    include_geojson : bool, optional
        Include an associated GeoJSON feature collection in the response.
    return_probability : bool, optional
        Include the localization probability density for each galaxy.
    sort_by : str, optional
        Column to sort by; one of ``distmpc``, ``redshift``, ``name``,
        ``mstar``, ``prob``, ``mstar_prob_weighted``, ``sfr_fuv``,
        ``magb``, ``magk``. Sorting by ``prob`` or
        ``mstar_prob_weighted`` requires ``localization_dateobs``.
    sort_order : str, optional
        ``"asc"`` or ``"desc"``; required when ``sort_by`` is provided.
    page_number, num_per_page : int, optional
        Pagination controls. ``num_per_page`` can be no larger than
        10000.
    """
    params: dict[str, str | int | float | bool] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if catalog_name is not None:
        params["catalog_name"] = catalog_name
    if galaxy_name is not None:
        params["galaxyName"] = galaxy_name
    if ra is not None:
        params["ra"] = ra
    if dec is not None:
        params["dec"] = dec
    if radius is not None:
        params["radius"] = radius
    if min_redshift is not None:
        params["minRedshift"] = min_redshift
    if max_redshift is not None:
        params["maxRedshift"] = max_redshift
    if min_distance is not None:
        params["minDistance"] = min_distance
    if max_distance is not None:
        params["maxDistance"] = max_distance
    if min_mstar is not None:
        params["minMstar"] = min_mstar
    if max_mstar is not None:
        params["maxMstar"] = max_mstar
    if localization_dateobs is not None:
        params["localizationDateobs"] = localization_dateobs
    if localization_name is not None:
        params["localizationName"] = localization_name
    if localization_cumprob is not None:
        params["localizationCumprob"] = localization_cumprob
    if include_geojson:
        params["includeGeoJSON"] = True
    if return_probability:
        params["returnProbability"] = True
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_order is not None:
        params["sortOrder"] = sort_order
    response = client.get("/api/galaxy_catalog", params=params)
    return GalaxiesPageResponse.model_validate(unwrap(response))


def fetch_galaxy_catalogs(client: httpx.Client) -> list[GalaxyCatalogCountResponse]:
    """Retrieve the galaxy catalog names and their galaxy counts.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/galaxy_catalog", params={"catalogNamesOnly": True})
    return [
        GalaxyCatalogCountResponse.model_validate(item) for item in unwrap(response)
    ]


def post_galaxy_catalog(client: httpx.Client, payload: GalaxyCatalogPost) -> None:
    """Ingest a galaxy catalog. Requires the System admin ACL.

    The ingestion runs asynchronously on the server; a success response
    only means the ingestion was started.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : GalaxyCatalogPost
        The catalog to ingest. ``catalog_data`` maps column names to
        equal-length lists; ``ra``, ``dec``, and ``name`` are required
        columns, with ``ra`` in ``[0, 360)`` degrees and ``dec`` in
        ``[-90, 90]`` degrees.
    """
    unwrap(
        client.post("/api/galaxy_catalog", json=payload.model_dump(exclude_none=True))
    )


def delete_galaxy_catalog(client: httpx.Client, catalog_name: str) -> None:
    """Delete a galaxy catalog. Requires the System admin ACL.

    The deletion runs asynchronously on the server; a success response
    only means the deletion was started.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    catalog_name : str
        Name of the galaxy catalog to delete.
    """
    unwrap(client.delete(f"/api/galaxy_catalog/{catalog_name}"))


def post_galaxy_catalog_ascii(
    client: httpx.Client,
    payload: GalaxyCatalogASCIIPost,
) -> None:
    """Upload galaxies from an ASCII file. Requires the Upload data ACL.

    The ingestion runs asynchronously on the server; a success response
    only means the ingestion was started.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : GalaxyCatalogASCIIPost
        The catalog to upload. ``catalog_data`` is the file content as a
        comma-separated ASCII table with ``ra``, ``dec``, and ``name``
        columns required.
    """
    unwrap(
        client.post(
            "/api/galaxy_catalog/ascii",
            json=payload.model_dump(by_alias=True, exclude_none=True),
        )
    )


def post_galaxy_catalog_regalade(
    client: httpx.Client,
    *,
    file_name: str | None = None,
    file_url: str | None = None,
) -> None:
    """Ingest the REGALADE galaxy catalog. Requires the System Admin ACL.

    The ingestion runs asynchronously on the server; a success response
    only means the ingestion was started.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    file_name : str, optional
        Name of the ``.fits`` file in the server's data directory. If
        neither ``file_name`` nor ``file_url`` is provided, the server
        looks for ``regalade_v2.fits`` in its data directory.
    file_url : str, optional
        URL of the ``.fits`` file containing the galaxies.
    """
    payload: dict[str, str] = {}
    if file_name is not None:
        payload["file_name"] = file_name
    if file_url is not None:
        payload["file_url"] = file_url
    unwrap(client.post("/api/galaxy_catalog/regalade", json=payload))


def post_galaxy_catalog_ned(
    client: httpx.Client,
    *,
    file_name: str | None = None,
    file_url: str | None = None,
) -> None:
    """Ingest the NEDLVS galaxy catalog. Requires the System Admin ACL.

    The ingestion runs asynchronously on the server; a success response
    only means the ingestion was started.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    file_name : str, optional
        Name of the ``.fits`` file in the server's data directory. If
        neither ``file_name`` nor ``file_url`` is provided, the server
        looks for ``NEDLVS_20260424.fits`` in its data directory.
    file_url : str, optional
        URL of the ``.fits`` file containing the galaxies.
    """
    payload: dict[str, str] = {}
    if file_name is not None:
        payload["file_name"] = file_name
    if file_url is not None:
        payload["file_url"] = file_url
    unwrap(client.post("/api/galaxy_catalog/ned", json=payload))
