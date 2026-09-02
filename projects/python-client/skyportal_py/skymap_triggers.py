"""Typed endpoint functions for ``/api/skymap_trigger``."""

from __future__ import annotations

import httpx
from skyportal_py_models.skymap_triggers import SkymapTriggerQueueResponse

from skyportal_py._http import unwrap

__all__ = [
    "SkymapTriggerQueueResponse",
]


def fetch_skymap_triggers(
    client: httpx.Client,
    allocation_id: int,
) -> SkymapTriggerQueueResponse:
    """Retrieve the skymap-based triggers queued on an allocation's facility.

    The allocation's instrument must have a remote observation plan API that
    implements ``queued_skymap``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation whose queue is retrieved.
    """
    response = client.get(f"/api/skymap_trigger/{allocation_id}")
    return SkymapTriggerQueueResponse.model_validate(unwrap(response))


def post_skymap_trigger(
    client: httpx.Client,
    allocation_id: int,
    localization_id: int,
    *,
    integrated_probability: float = 0.95,
) -> None:
    """Send a skymap-based trigger to an allocation's facility.

    The server converts the localization into the instrument's field tiles
    down to the requested credible level and submits them through the
    instrument's remote observation plan API, which must implement
    ``send_skymap``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation to trigger.
    localization_id : int
        ID of the localization (skymap) to send.
    integrated_probability : float, optional
        Cumulative probability of the skymap to cover. Defaults to 0.95.
    """
    payload = {
        "allocation_id": allocation_id,
        "localization_id": localization_id,
        "integrated_probability": integrated_probability,
    }
    unwrap(client.post("/api/skymap_trigger", json=payload))


def delete_skymap_trigger(
    client: httpx.Client,
    allocation_id: int,
    trigger_name: str,
) -> None:
    """Remove a queued skymap-based trigger from an allocation's facility.

    The allocation's instrument must have a remote observation plan API that
    implements ``remove_skymap``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation whose queue is modified.
    trigger_name : str
        Name of the queued trigger to remove.
    """
    unwrap(
        client.request(
            "DELETE",
            f"/api/skymap_trigger/{allocation_id}",
            json={"trigger_name": trigger_name},
        )
    )
