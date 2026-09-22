"""Typed endpoint functions for ``/api/user``."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import UserResponse
from skyportal_py_models.users import UserPost, UserPostResponse, UsersPageResponse

from skyportal_py._http import UNSET, unwrap

__all__ = [
    "UserPost",
    "UserPostResponse",
    "UserResponse",
    "UsersPageResponse",
]


def fetch_users(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
    email: str | None = None,
    role: str | None = None,
    acl: str | None = None,
    group: str | None = None,
    stream: str | None = None,
    include_expired: bool = False,
    sort_by: str = "username",
    sort_order: str = "asc",
) -> UsersPageResponse:
    """Query users, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls. ``num_per_page`` defaults to the server's page
        size.
    first_name, last_name, username, email : str, optional
        Keep users whose field matches.
    role, acl : str, optional
        Keep users holding this role / ACL.
    group, stream : str, optional
        Keep users belonging to the group / stream with this name.
    include_expired : bool, optional
        Also include deactivated (expired) accounts.
    sort_by : str, optional
        Column to sort on; one of "username", "firstName", "lastName",
        "contactEmail", or "createdAt".
    sort_order : str, optional
        "asc" or "desc".
    """
    params = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "firstName": first_name,
        "lastName": last_name,
        "username": username,
        "email": email,
        "role": role,
        "acl": acl,
        "group": group,
        "stream": stream,
        "includeExpired": include_expired,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    response = client.get(
        "/api/user",
        params={key: value for key, value in params.items() if value is not None},
    )
    return UsersPageResponse.model_validate(unwrap(response))


def fetch_user(client: httpx.Client, user_id: int) -> UserResponse:
    """Retrieve a single user by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int
        ID of the user.
    """
    response = client.get(f"/api/user/{user_id}")
    return UserResponse.model_validate(unwrap(response))


def post_user(client: httpx.Client, payload: UserPost) -> UserPostResponse:
    """Add a new user (requires the "Manage users" ACL).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : UserPost
        The user to add. If ``roles`` is omitted, the server assigns its
        configured default role; if ``group_ids_and_admin`` (pairs of
        ``[group_id, admin]``) is omitted, the server adds the user to its
        default groups.
    """
    response = client.post(
        "/api/user",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return UserPostResponse.model_validate(unwrap(response))


def update_user(
    client: httpx.Client,
    user_id: int,
    *,
    expiration_date: str | None = UNSET,
) -> None:
    """Update a user record (requires the "Manage users" ACL).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int
        ID of the user to update.
    expiration_date : str or None, optional
        Arrow-parseable date string (e.g. ``"2020-01-01"``). After this
        date the account is deactivated and cannot access the application.
        Pass None explicitly to clear an existing expiration date.
    """
    payload: dict[str, str | None] = {}
    if expiration_date is not UNSET:
        payload["expirationDate"] = expiration_date
    unwrap(client.patch(f"/api/user/{user_id}", json=payload))


def delete_user(client: httpx.Client, user_id: int) -> None:
    """Delete a user (requires the "Manage users" ACL).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int
        ID of the user to delete.
    """
    unwrap(client.delete(f"/api/user/{user_id}"))
