"""Typed endpoint functions for ``/api/observing_run``."""

from __future__ import annotations

import httpx
from skyportal_py_models.observing_runs import (
    ObservingRunPost,
    ObservingRunPostResponse,
    ObservingRunResponse,
    ObservingRunUpdate,
)

from skyportal_py._http import unwrap

__all__ = [
    "ObservingRunPost",
    "ObservingRunPostResponse",
    "ObservingRunResponse",
    "ObservingRunUpdate",
]


def fetch_observing_runs(
    client: httpx.Client,
    *,
    upcoming_only: bool = False,
) -> list[ObservingRunResponse]:
    """Retrieve all observing runs.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    upcoming_only : bool, optional
        Return only runs that have not finished yet.
    """
    params = {"upcomingOnly": True} if upcoming_only else {}
    response = client.get("/api/observing_run", params=params)
    return [ObservingRunResponse.model_validate(item) for item in unwrap(response)]


def fetch_observing_run(client: httpx.Client, run_id: int) -> ObservingRunResponse:
    """Retrieve a single observing run by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    run_id : int
        ID of the observing run.
    """
    response = client.get(f"/api/observing_run/{run_id}")
    return ObservingRunResponse.model_validate(unwrap(response))


def post_observing_run(
    client: httpx.Client,
    payload: ObservingRunPost,
) -> ObservingRunPostResponse:
    """Create an observing run.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ObservingRunPost
        The run to create. ``calendar_date`` is the local calendar date of
        the run in ISO format, e.g. ``"2026-09-01"``; ``duration`` is the
        number of nights.
    """
    response = client.post(
        "/api/observing_run", json=payload.model_dump(exclude_none=True)
    )
    return ObservingRunPostResponse.model_validate(unwrap(response))


def delete_observing_run(client: httpx.Client, run_id: int) -> None:
    """Delete an observing run.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    run_id : int
        ID of the observing run to delete.
    """
    unwrap(client.delete(f"/api/observing_run/{run_id}"))


def update_observing_run(
    client: httpx.Client,
    run_id: int,
    payload: ObservingRunUpdate,
) -> None:
    """Update an observing run.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    run_id : int
        ID of the observing run to update. Only the owner of a run may
        modify it.
    payload : ObservingRunUpdate
        Fields to change. The run's end time is recomputed server-side
        afterwards.
    """
    unwrap(
        client.put(
            f"/api/observing_run/{run_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def update_observing_run_not_observed(
    client: httpx.Client,
    run_id: int,
    current_status: str,
    new_status: str,
) -> None:
    """Bulk-restatus the assignments of an observing run.

    Every assignment on the run whose status equals ``current_status`` is
    moved to ``new_status``; the others are left alone.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    run_id : int
        ID of the observing run.
    current_status : str
        Status an assignment must currently have to be updated, e.g.
        ``"pending"``.
    new_status : str
        Status to apply, e.g. ``"not observed"``.
    """
    unwrap(
        client.put(
            f"/api/observing_run/{run_id}/not_observed",
            json={"current_status": current_status, "new_status": new_status},
        )
    )
