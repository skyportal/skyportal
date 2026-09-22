"""Typed endpoint functions for ``/api/filters``."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import FilterResponse
from skyportal_py_models.filters import FilterPatch, FilterPost, FilterPostResponse

from skyportal_py._http import unwrap

__all__ = [
    "FilterPatch",
    "FilterPost",
    "FilterPostResponse",
    "FilterResponse",
]


def fetch_filters(client: httpx.Client) -> list[FilterResponse]:
    """Retrieve all filters belonging to the token's groups.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/filters")
    return [FilterResponse.model_validate(item) for item in unwrap(response)]


def fetch_filter(client: httpx.Client, filter_id: int) -> FilterResponse:
    """Retrieve a single filter by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    filter_id : int
        ID of the filter.
    """
    response = client.get(f"/api/filters/{filter_id}")
    return FilterResponse.model_validate(unwrap(response))


def post_filter(client: httpx.Client, payload: FilterPost) -> FilterPostResponse:
    """Create a filter.

    Requires the "Upload data" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : FilterPost
        The filter to create. ``broker_id`` identifies the broker the filter
        runs on, if any, and ``altdata`` holds arbitrary extra JSON.
    """
    response = client.post("/api/filters", json=payload.model_dump(exclude_none=True))
    return FilterPostResponse.model_validate(unwrap(response))


def update_filter(
    client: httpx.Client,
    filter_id: int,
    payload: FilterPatch,
) -> None:
    """Update a filter.

    Only the provided fields are sent; omitted fields are left unchanged.
    ``group_id`` and ``stream_id`` cannot be changed and are accepted only
    when they match the filter's current values. Renaming a filter that is
    attached to a broker also renames it on the broker, and fails if the
    broker rejects the rename. ``autosave`` controls whether objects passing
    the filter during broker ingestion are saved as sources to the filter's
    group. Requires the "Upload data" permission and group- or system-admin
    access to the filter's group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    filter_id : int
        ID of the filter to update.
    payload : FilterPatch
        The fields to change.
    """
    unwrap(
        client.patch(
            f"/api/filters/{filter_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def delete_filter(client: httpx.Client, filter_id: int) -> None:
    """Delete a filter.

    Requires the "Upload data" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    filter_id : int
        ID of the filter to delete.
    """
    unwrap(client.delete(f"/api/filters/{filter_id}"))
