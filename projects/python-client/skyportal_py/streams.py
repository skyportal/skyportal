"""Typed endpoint functions for ``/api/streams``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models._cyclic import StreamResponse
from skyportal_py_models.streams import StreamPostResponse, StreamUserPostResponse

from skyportal_py._http import unwrap

__all__ = [
    "StreamPostResponse",
    "StreamResponse",
    "StreamUserPostResponse",
]


def fetch_streams(client: httpx.Client) -> list[StreamResponse]:
    """Retrieve the alert streams visible to the token.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/streams")
    return [StreamResponse.model_validate(item) for item in unwrap(response)]


def fetch_stream(client: httpx.Client, stream_id: int) -> StreamResponse:
    """Retrieve a single alert stream by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    stream_id : int
        ID of the stream.
    """
    response = client.get(f"/api/streams/{stream_id}")
    return StreamResponse.model_validate(unwrap(response))


def post_stream(
    client: httpx.Client,
    name: str,
    *,
    altdata: dict[str, Any] | None = None,
    auto_join: bool = False,
) -> StreamPostResponse:
    """Create a new alert stream. Requires the System admin ACL.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str
        The stream name.
    altdata : dict, optional
        Misc. metadata stored as JSON, e.g.
        ``{"collection": "ZTF_alerts", "selector": [1, 2]}``.
    auto_join : bool, optional
        Allow any user to add themselves to the stream. Auto-join streams
        are visible to all users.
    """
    payload: dict[str, Any] = {"name": name, "auto_join": auto_join}
    if altdata is not None:
        payload["altdata"] = altdata
    response = client.post("/api/streams", json=payload)
    return StreamPostResponse.model_validate(unwrap(response))


def update_stream(
    client: httpx.Client,
    stream_id: int,
    name: str,
    *,
    altdata: dict[str, Any] | None = None,
    auto_join: bool | None = None,
) -> None:
    """Update an alert stream. Requires the System admin ACL.

    Omitted optional fields are left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    stream_id : int
        ID of the stream to update.
    name : str
        The stream name; required by the server even if unchanged.
    altdata : dict, optional
        New misc. metadata stored as JSON.
    auto_join : bool, optional
        Whether any user may add themselves to the stream.
    """
    payload: dict[str, Any] = {"name": name}
    if altdata is not None:
        payload["altdata"] = altdata
    if auto_join is not None:
        payload["auto_join"] = auto_join
    unwrap(client.patch(f"/api/streams/{stream_id}", json=payload))


def delete_stream(client: httpx.Client, stream_id: int) -> None:
    """Delete an alert stream. Requires the System admin ACL.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    stream_id : int
        ID of the stream to delete.
    """
    unwrap(client.delete(f"/api/streams/{stream_id}"))


def post_stream_user(
    client: httpx.Client,
    stream_id: int,
    user_id: int,
) -> StreamUserPostResponse:
    """Grant a user access to an alert stream.

    System admins may add any user; a non-admin may add only themselves,
    and only to an auto-join stream.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    stream_id : int
        ID of the stream.
    user_id : int
        ID of the user to be granted stream access.
    """
    response = client.post(f"/api/streams/{stream_id}/users", json={"user_id": user_id})
    return StreamUserPostResponse.model_validate(unwrap(response))


def delete_stream_user(client: httpx.Client, stream_id: int, user_id: int) -> None:
    """Revoke a user's access to an alert stream. Requires System admin.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    stream_id : int
        ID of the stream.
    user_id : int
        ID of the user whose stream access is revoked.
    """
    unwrap(client.delete(f"/api/streams/{stream_id}/users/{user_id}"))
