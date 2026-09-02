"""Typed endpoint functions for the instance introspection endpoints."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models.system import (
    DBInfoResponse,
    GitLogEntryResponse,
    SysInfoResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "DBInfoResponse",
    "GitLogEntryResponse",
    "SysInfoResponse",
]


def fetch_sysinfo(client: httpx.Client) -> SysInfoResponse:
    """Retrieve system and deployment information.

    The git log is capped at the 100 most recent non-merge commits, with
    "bump" and "pin" commits filtered out.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/sysinfo")
    return SysInfoResponse.model_validate(unwrap(response))


def fetch_dbinfo(client: httpx.Client) -> DBInfoResponse:
    """Retrieve whether the sources table is empty and the Postgres version.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/internal/dbinfo")
    return DBInfoResponse.model_validate(unwrap(response))


def fetch_altdata_info(client: httpx.Client) -> Any:  # noqa: ANN401 -- shape depends on query
    """Retrieve the catalog of altdata keys carried by accessible sources.

    The response shape varies with the endpoint's query arguments, so it is
    returned unmodelled.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    return unwrap(client.get("/api/internal/altdata_info"))


def fetch_annotations_info(client: httpx.Client) -> Any:  # noqa: ANN401 -- shape depends on query
    """Retrieve the catalog of annotation origins and keys.

    The response shape varies with the endpoint's query arguments, so it is
    returned unmodelled.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    return unwrap(client.get("/api/internal/annotations_info"))


def fetch_config(client: httpx.Client) -> dict[str, Any]:
    """Retrieve the parts of the instance config exposed to clients.

    The response is an open-ended camelCase mapping whose keys vary with the
    deployed SkyPortal version, so it is returned unmodelled. Typical keys
    include ``"invitationsEnabled"``, ``"cosmology"``,
    ``"allowedSpectrumTypes"``, ``"defaultSpectrumType"``,
    ``"gcnNoticeTypes"``, ``"colorPalette"`` and ``"publicGroupName"``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/config")
    return unwrap(response)


def fetch_db_stats(client: httpx.Client) -> dict[str, Any]:
    """Retrieve basic database statistics (requires "System admin").

    The response is an open-ended mapping keyed by human-readable phrases such
    as ``"Number of candidates"`` and ``"Latest cron job run times &
    statuses"``, so it is returned unmodelled. The photometry count is
    approximate, coming from ``pg_class.reltuples``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/db_stats")
    return unwrap(response)


def fetch_enum_types(client: httpx.Client) -> dict[str, Any]:
    """Retrieve the enumerated value lists the instance accepts.

    The response is an open-ended mapping of upper-case names to lists of
    allowed values, and the set of names varies with the deployed SkyPortal
    version, so it is returned unmodelled. Typical keys include
    ``"ALLOWED_SPECTRUM_TYPES"``, ``"ALLOWED_MAGSYSTEMS"``,
    ``"ALLOWED_BANDPASSES"``, ``"THUMBNAIL_TYPES"``, ``"FOLLOWUP_PRIORITIES"``,
    ``"ALLOWED_API_CLASSNAMES"``, ``"ANALYSIS_TYPES"``,
    ``"ANALYSIS_INPUT_TYPES"`` and ``"AUTHENTICATION_TYPES"``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/enum_types")
    return unwrap(response)
