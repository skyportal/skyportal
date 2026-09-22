"""Typed endpoint functions for ``/api/group_admission_requests``."""

from __future__ import annotations

import httpx
from skyportal_py_models.group_admission_requests import (
    GroupAdmissionRequestPostResponse,
    GroupAdmissionRequestResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "GroupAdmissionRequestPostResponse",
    "GroupAdmissionRequestResponse",
]


def fetch_group_admission_request(
    client: httpx.Client,
    admission_request_id: int,
) -> GroupAdmissionRequestResponse:
    """Retrieve a single group admission request by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    admission_request_id : int
        ID of the admission request. Only the requesting user and admins of
        the target group may read it.
    """
    response = client.get(f"/api/group_admission_requests/{admission_request_id}")
    return GroupAdmissionRequestResponse.model_validate(unwrap(response))


def fetch_group_admission_requests(
    client: httpx.Client,
    *,
    group_id: int | None = None,
) -> list[GroupAdmissionRequestResponse]:
    """Retrieve the group admission requests visible to the token.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int, optional
        Only return requests to join this group.
    """
    params: dict[str, int] = {}
    if group_id is not None:
        params["groupID"] = group_id
    response = client.get("/api/group_admission_requests", params=params)
    return [GroupAdmissionRequestResponse.model_validate(r) for r in unwrap(response)]


def post_group_admission_request(
    client: httpx.Client,
    group_id: int,
    user_id: int,
) -> GroupAdmissionRequestPostResponse:
    """Request admission to a group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group to join. It must not be a single-user group, and the
        requesting user must already have access to all of its streams.
    user_id : int
        ID of the requesting user; requests cannot be made on behalf of
        others. If the group auto-accepts requests, the request is created
        as ``"accepted"`` and the user is added to the group immediately.
    """
    payload: dict[str, int] = {"groupID": group_id, "userID": user_id}
    response = client.post("/api/group_admission_requests", json=payload)
    return GroupAdmissionRequestPostResponse.model_validate(unwrap(response))


def update_group_admission_request(
    client: httpx.Client,
    admission_request_id: int,
    status: str,
) -> None:
    """Accept, decline, or reset a group admission request.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    admission_request_id : int
        ID of the admission request. Only admins of the target group may
        change its status.
    status : str
        One of ``"pending"``, ``"accepted"``, or ``"declined"``. The
        requesting user is notified of the new status.
    """
    unwrap(
        client.patch(
            f"/api/group_admission_requests/{admission_request_id}",
            json={"status": status},
        )
    )


def delete_group_admission_request(
    client: httpx.Client,
    admission_request_id: int,
) -> None:
    """Withdraw a group admission request.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    admission_request_id : int
        ID of the admission request. Only the requesting user may delete it.
    """
    unwrap(client.delete(f"/api/group_admission_requests/{admission_request_id}"))
