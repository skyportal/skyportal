"""Typed endpoint functions for ``/api/spatial_catalog``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models.spatial_catalogs import (
    SpatialCatalogEntryResponse,
    SpatialCatalogPostResponse,
    SpatialCatalogResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "SpatialCatalogEntryResponse",
    "SpatialCatalogPostResponse",
    "SpatialCatalogResponse",
]


def fetch_spatial_catalog(
    client: httpx.Client, catalog_id: int
) -> SpatialCatalogResponse:
    """Retrieve a single spatial catalog, including its entries.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    catalog_id : int
        ID of the spatial catalog.
    """
    response = client.get(f"/api/spatial_catalog/{catalog_id}")
    return SpatialCatalogResponse.model_validate(unwrap(response))


def fetch_spatial_catalogs(client: httpx.Client) -> list[SpatialCatalogResponse]:
    """Retrieve all spatial catalogs, each with its entry count.

    The returned catalogs carry ``entries_count`` but not the entries
    themselves; use :func:`fetch_spatial_catalog` for the entries.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/spatial_catalog")
    return [
        SpatialCatalogResponse.model_validate(catalog) for catalog in unwrap(response)
    ]


def post_spatial_catalog(
    client: httpx.Client,
    catalog_name: str,
    catalog_data: dict[str, list[Any]],
) -> SpatialCatalogPostResponse:
    """Ingest a spatial catalog.

    The entry ingestion runs asynchronously on the server; the returned
    ID is available immediately but the entries may take a while to
    appear.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    catalog_name : str
        Name of the spatial catalog. Reused if it already exists.
    catalog_data : dict of str to list
        Maps column names to equal-length lists. ``name``, ``ra``, and
        ``dec`` are required, with ``ra`` in ``[0, 360)`` degrees and
        ``dec`` in ``[-90, 90]`` degrees. Either ``radius`` (cone) or
        ``amaj``, ``amin``, and ``phi`` (ellipse) are also required.
    """
    payload = {"catalog_name": catalog_name, "catalog_data": catalog_data}
    response = client.post("/api/spatial_catalog", json=payload)
    return SpatialCatalogPostResponse.model_validate(unwrap(response))


def delete_spatial_catalog(client: httpx.Client, catalog_id: int) -> None:
    """Delete a spatial catalog.

    The deletion runs asynchronously on the server; a success response
    only means the deletion was started.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    catalog_id : int
        ID of the spatial catalog to delete.
    """
    unwrap(client.delete(f"/api/spatial_catalog/{catalog_id}"))


def post_spatial_catalog_ascii(
    client: httpx.Client,
    catalog_name: str,
    catalog_data: str,
) -> SpatialCatalogPostResponse:
    """Upload a spatial catalog from an ASCII file.

    Requires the Upload data ACL. The entry ingestion runs
    asynchronously on the server; the returned ID is available
    immediately but the entries may take a while to appear.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    catalog_name : str
        Name of the spatial catalog. Reused if it already exists.
    catalog_data : str
        File content as a comma-separated ASCII table. ``name``, ``ra``,
        and ``dec`` columns are required, plus either ``radius`` (cone)
        or ``amaj``, ``amin``, and ``phi`` (ellipse).
    """
    payload = {"catalogName": catalog_name, "catalogData": catalog_data}
    response = client.post("/api/spatial_catalog/ascii", json=payload)
    return SpatialCatalogPostResponse.model_validate(unwrap(response))
