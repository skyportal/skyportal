"""Typed endpoint functions for ``/api/catalog_queries`` and ``/api/catalogs``."""

from __future__ import annotations

import httpx
from skyportal_py_models.catalog_queries import CatalogQueryPost

from skyportal_py._http import unwrap

__all__ = [
    "CatalogQueryPost",
]


def post_catalog_query(client: httpx.Client, payload: CatalogQueryPost) -> None:
    """Submit a catalog query, retrieving sources in a GCN localization.

    The query runs asynchronously on the server; a success response only
    means the query was started. Retrieved sources are saved to the
    target groups and the allocation's group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : CatalogQueryPost
        The query to submit. ``payload`` must contain ``catalogName``
        (one of ``ZTF-Fink``, ``LSXPS``, ``Gaia``, or ``TESS``),
        ``localizationDateobs``, ``localizationName``, ``startDate``,
        ``endDate``, and (for ``ZTF-Fink``) ``localizationCumprob``.
    """
    response = client.post(
        "/api/catalog_queries", json=payload.model_dump(exclude_none=True)
    )
    unwrap(response)


def post_swift_lsxps_query(
    client: httpx.Client,
    *,
    telescope_name: str | None = None,
    group_ids: list[int] | None = None,
) -> None:
    """Post Swift LSXPS transients as sources.

    The query runs asynchronously on the server; a success response only
    means the query was started. Repeated posting skips existing
    sources.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    telescope_name : str, optional
        Nickname of the telescope to assign this catalog to. Server
        default is ``"Swift"``.
    group_ids : list of int, optional
        Save the sources to these groups. If omitted, the server uses
        all of the token's accessible groups.
    """
    payload: dict[str, str | list[int]] = {}
    if telescope_name is not None:
        payload["telescope_name"] = telescope_name
    if group_ids is not None:
        payload["groupIDs"] = group_ids
    unwrap(client.post("/api/catalogs/swift_lsxps", json=payload))


def post_gaia_alerts_query(
    client: httpx.Client,
    *,
    telescope_name: str | None = None,
    group_ids: list[int] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """Post Gaia Photometric Alerts as sources.

    The query runs asynchronously on the server; a success response only
    means the query was started. Repeated posting skips existing
    sources.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    telescope_name : str, optional
        Nickname of the telescope to assign this catalog to. Server
        default is ``"Gaia"``.
    group_ids : list of int, optional
        Save the sources to these groups. If omitted, the server uses
        all of the token's accessible groups.
    start_date, end_date : str, optional
        Only include alerts in this date range, as arrow-parsable
        strings, e.g. ``"2020-01-01"``.
    """
    payload: dict[str, str | list[int]] = {}
    if telescope_name is not None:
        payload["telescope_name"] = telescope_name
    if group_ids is not None:
        payload["groupIDs"] = group_ids
    if start_date is not None:
        payload["startDate"] = start_date
    if end_date is not None:
        payload["endDate"] = end_date
    unwrap(client.post("/api/catalogs/gaia_alerts", json=payload))
