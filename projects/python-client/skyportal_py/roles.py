"""Typed endpoint functions for ``/api/roles``."""

from __future__ import annotations

import httpx
from skyportal_py_models.invitations import RoleResponse

from skyportal_py._http import unwrap

__all__ = [
    "RoleResponse",
]


def fetch_roles(client: httpx.Client) -> list[RoleResponse]:
    """Retrieve all roles, each with the IDs of its ACLs.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/roles")
    return [RoleResponse.model_validate(role) for role in unwrap(response)]


def post_user_role(
    client: httpx.Client,
    user_id: int,
    role_ids: list[str],
) -> None:
    """Grant roles to a user (requires the "Manage users" ACL).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int
        ID of the user to grant the roles to.
    role_ids : list of str
        IDs of the roles to grant; every ID must name an existing role.
    """
    unwrap(client.post(f"/api/user/{user_id}/roles", json={"roleIds": role_ids}))


def delete_user_role(client: httpx.Client, user_id: int, role_id: str) -> None:
    """Remove a role from a user (requires the "Manage users" ACL).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    user_id : int
        ID of the user to remove the role from.
    role_id : str
        ID of the role to remove; the user must currently have it.
    """
    unwrap(client.delete(f"/api/user/{user_id}/roles/{role_id}"))
