"""Typed endpoint functions for ``/api/assignment``."""

from __future__ import annotations

import httpx
from skyportal_py_models.assignments import (
    AssignmentPost,
    AssignmentResponse,
    FollowupPriority,
)
from skyportal_py_models.followup_requests import AssignmentPostResponse

from skyportal_py._http import unwrap

__all__ = [
    "AssignmentPost",
    "AssignmentPostResponse",
    "AssignmentResponse",
    "FollowupPriority",
]

"""Allowed follow-up priorities, lowest (``"1"``) to highest (``"5"``)."""


def fetch_assignment(client: httpx.Client, assignment_id: int) -> AssignmentResponse:
    """Retrieve a single observing-run assignment by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    assignment_id : int
        ID of the assignment.
    """
    response = client.get(f"/api/assignment/{assignment_id}")
    return AssignmentResponse.model_validate(unwrap(response))


def fetch_assignments(client: httpx.Client) -> list[AssignmentResponse]:
    """Retrieve all observing-run assignments visible to the token.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/assignment")
    return [AssignmentResponse.model_validate(item) for item in unwrap(response)]


def post_assignment(
    client: httpx.Client,
    payload: AssignmentPost,
) -> AssignmentPostResponse:
    """Assign a target to a classical observing run.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : AssignmentPost
        The assignment to create. ``priority`` is a string from ``"1"``
        (lowest) to ``"5"`` (highest). The server rejects the assignment
        if the object is already assigned to the run.
    """
    response = client.post(
        "/api/assignment", json=payload.model_dump(exclude_none=True)
    )
    return AssignmentPostResponse.model_validate(unwrap(response))


def update_assignment(
    client: httpx.Client,
    assignment_id: int,
    *,
    comment: str | None = None,
    status: str | None = None,
    priority: str | None = None,
) -> None:
    """Update an observing-run assignment.

    Only the provided fields are sent; omitted fields are left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    assignment_id : int
        ID of the assignment to update.
    comment : str, optional
        New comment on the assignment.
    status : str, optional
        New status, e.g. ``"done"``, ``"not done"``, or ``"pending"``.
    priority : str, optional
        New priority, from ``"1"`` (lowest) to ``"5"`` (highest).
    """
    fields = {"comment": comment, "status": status, "priority": priority}
    payload = {name: value for name, value in fields.items() if value is not None}
    unwrap(client.put(f"/api/assignment/{assignment_id}", json=payload))


def delete_assignment(client: httpx.Client, assignment_id: int) -> None:
    """Delete an observing-run assignment.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    assignment_id : int
        ID of the assignment to delete.
    """
    unwrap(client.delete(f"/api/assignment/{assignment_id}"))
