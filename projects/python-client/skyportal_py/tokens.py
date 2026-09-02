"""Typed endpoint functions for ``/api/internal/tokens``."""

from __future__ import annotations

import httpx
from skyportal_py_models.tokens import ApiTokenResponse, TokenPostResponse

from skyportal_py._http import unwrap

__all__ = [
    "ApiTokenResponse",
    "TokenPostResponse",
]


def fetch_tokens(
    client: httpx.Client, *, user_id: int | None = None
) -> list[ApiTokenResponse]:
    """Retrieve the API tokens visible to the requesting user.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int, optional
        Keep only tokens created by this user.
    """
    params = {} if user_id is None else {"userID": user_id}
    response = client.get("/api/internal/tokens", params=params)
    return [ApiTokenResponse.model_validate(token) for token in unwrap(response)]


def fetch_token(client: httpx.Client, token_id: str) -> ApiTokenResponse:
    """Retrieve a single API token by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    token_id : str
        ID of the token.
    """
    response = client.get(f"/api/internal/tokens/{token_id}")
    return ApiTokenResponse.model_validate(unwrap(response))


def post_token(
    client: httpx.Client,
    name: str,
    acls: list[str],
    *,
    user_id: int | None = None,
) -> TokenPostResponse:
    """Create a new API token.

    The token may only carry ACLs its owner holds, and non-admins may only
    create tokens for themselves.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str
        Name of the token; must be unique among the owner's tokens.
    acls : list of str
        ACL IDs to grant the token.
    user_id : int, optional
        UserResponse to create the token for; defaults to the requesting user.
    """
    payload: dict[str, str | list[str] | int] = {"name": name, "acls": acls}
    if user_id is not None:
        payload["user_id"] = user_id
    response = client.post("/api/internal/tokens", json=payload)
    return TokenPostResponse.model_validate(unwrap(response))


def update_token(
    client: httpx.Client,
    token_id: str,
    *,
    name: str | None = None,
    acls: list[str] | None = None,
    user_id: int | None = None,
) -> None:
    """Update an API token's name and/or ACLs.

    Omitted fields are left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    token_id : str
        ID of the token to update.
    name : str, optional
        New name of the token.
    acls : list of str, optional
        New list of ACL IDs for the token.
    user_id : int, optional
        UserResponse whose permissions the new ACLs are checked against; defaults
        to the requesting user.
    """
    fields = {"name": name, "acls": acls, "user_id": user_id}
    payload = {key: value for key, value in fields.items() if value is not None}
    unwrap(client.put(f"/api/internal/tokens/{token_id}", json=payload))


def delete_token(client: httpx.Client, token_id: str) -> None:
    """Delete an API token.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    token_id : str
        ID of the token to delete.
    """
    unwrap(client.delete(f"/api/internal/tokens/{token_id}"))
