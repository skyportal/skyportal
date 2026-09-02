"""Typed endpoint functions for ``/api/listing``."""

from __future__ import annotations

import httpx
from skyportal_py_models.listings import (
    ListingPost,
    ListingPostResponse,
    ListingResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "ListingPost",
    "ListingPostResponse",
    "ListingResponse",
]


def fetch_listings(
    client: httpx.Client,
    *,
    user_id: int | None = None,
    list_name: str | None = None,
) -> list[ListingResponse]:
    """Retrieve the objects a user has saved to their lists.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int, optional
        UserResponse whose listings to retrieve. Defaults to the token's own user.
    list_name : str, optional
        Only return entries of this list, e.g. ``"favorites"``. If omitted,
        entries from all of the user's lists are returned.
    """
    path = "/api/listing" if user_id is None else f"/api/listing/{user_id}"
    params: dict[str, str] = {}
    if list_name is not None:
        params["listName"] = list_name
    response = client.get(path, params=params)
    return [ListingResponse.model_validate(listing) for listing in unwrap(response)]


def post_listing(
    client: httpx.Client,
    payload: ListingPost,
) -> ListingPostResponse:
    """Add an object to one of a user's lists.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ListingPost
        The entry to create. ``list_name`` is user-defined and must start
        with an alphanumeric character or underscore; ``"favorites"`` and
        ``"rejected_candidates"`` have special meaning in the web app.
        ``user_id`` defaults to the token's own user, and only admins may
        add listings to other users' accounts. ``params`` is required for
        the ``"watchlist"`` list and must contain numeric ``arcsec`` (0 to
        3600) and ``cadence`` (1 or more) keys, plus an optional boolean
        ``end_of_night``. A given user, object, and list name combination
        may only be saved once.
    """
    response = client.post(
        "/api/listing",
        json=payload.model_dump(exclude_none=True),
    )
    return ListingPostResponse.model_validate(unwrap(response))


def update_listing(
    client: httpx.Client,
    listing_id: int,
    *,
    user_id: int | None = None,
    obj_id: str | None = None,
    list_name: str | None = None,
) -> None:
    """Update an existing listing.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    listing_id : int
        ID of the listing to update.
    user_id : int, optional
        Move the listing to this user. Only system admins may set it to
        another user. Defaults to leaving the owner unchanged.
    obj_id : str, optional
        Point the listing at this object instead.
    list_name : str, optional
        Rename the list this entry belongs to; must start with an
        alphanumeric character or underscore.
    """
    payload: dict[str, str | int] = {}
    if user_id is not None:
        payload["user_id"] = user_id
    if obj_id is not None:
        payload["obj_id"] = obj_id
    if list_name is not None:
        payload["list_name"] = list_name
    unwrap(client.patch(f"/api/listing/{listing_id}", json=payload))


def delete_listing(client: httpx.Client, listing_id: int) -> None:
    """Remove a listing by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    listing_id : int
        ID of the listing to remove.
    """
    unwrap(client.delete(f"/api/listing/{listing_id}"))


def delete_listing_by_name(
    client: httpx.Client,
    obj_id: str,
    list_name: str,
    *,
    user_id: int | None = None,
) -> None:
    """Remove a listing identified by its object and list name.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the listed source.
    list_name : str
        Name of the list holding the entry, e.g. ``"favorites"``.
    user_id : int, optional
        Owner of the listing. Defaults to the token's own user.
    """
    payload: dict[str, str | int] = {"obj_id": obj_id, "list_name": list_name}
    if user_id is not None:
        payload["user_id"] = user_id
    unwrap(client.request("DELETE", "/api/listing", json=payload))
