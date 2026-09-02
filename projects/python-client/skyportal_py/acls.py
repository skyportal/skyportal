"""Typed endpoint functions for ``/api/acls``."""

from __future__ import annotations

import httpx

from skyportal_py._http import unwrap


def fetch_acls(client: httpx.Client) -> list[str]:
    """Retrieve the IDs of all ACLs.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/acls")
    return [str(acl_id) for acl_id in unwrap(response)]


def post_user_acl(
    client: httpx.Client,
    user_id: int,
    acl_ids: list[str],
) -> None:
    """Grant ACLs to a user (requires the "Manage users" ACL).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int
        ID of the user to grant the ACLs to.
    acl_ids : list of str
        IDs of the ACLs to grant; every ID must name an existing ACL.
    """
    unwrap(client.post(f"/api/user/{user_id}/acls", json={"aclIds": acl_ids}))


def delete_user_acl(client: httpx.Client, user_id: int, acl_id: str) -> None:
    """Remove an ACL from a user (requires the "Manage users" ACL).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int
        ID of the user to remove the ACL from.
    acl_id : str
        ID of the ACL to remove.
    """
    unwrap(client.delete(f"/api/user/{user_id}/acls/{acl_id}"))
