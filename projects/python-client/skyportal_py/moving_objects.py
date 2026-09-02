"""Typed endpoint functions for ``/api/moving_object``."""

from __future__ import annotations

import httpx
from skyportal_py_models.moving_objects import (
    MovingObjectFollowupPost,
    MovingObjectObservationResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "MovingObjectFollowupPost",
    "MovingObjectObservationResponse",
]


def post_moving_object_followup(
    client: httpx.Client,
    obj_name: str,
    payload: MovingObjectFollowupPost,
) -> list[MovingObjectObservationResponse]:
    """Find a continuous sequence of observations for a moving object.

    The object's ephemeris is looked up by name and matched against the
    instrument's fields; ``exposure_count`` exposures are then scheduled
    at the optimal times inside the requested window. An empty list is
    returned when no observable sequence long enough exists.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_name : str
        Name of the moving object, e.g. ``"2024 YR4"``.
    payload : MovingObjectFollowupPost
        The request. ``start_time`` and ``end_time`` are ISO-format
        datetimes less than 7 days apart. ``band`` is sent as the
        endpoint's ``filter`` field. ``primary_only`` restricts the
        search to the instrument's primary field grid (server default
        true), and ``airmass_limit``, ``moon_distance_limit`` and
        ``sun_altitude_limit`` default server-side to 2.5, 30 degrees
        and -18 degrees respectively.
    """
    response = client.post(
        f"/api/moving_object/{obj_name}/followup",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return [
        MovingObjectObservationResponse.model_validate(observation)
        for observation in unwrap(response)
    ]
