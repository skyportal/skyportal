"""Typed endpoint functions for ``/api/source_groups``."""

from __future__ import annotations

import httpx
from skyportal_py_models.source_groups import SourceGroupsPost

from skyportal_py._http import unwrap

__all__ = [
    "SourceGroupsPost",
]


def post_source_groups(client: httpx.Client, payload: SourceGroupsPost) -> None:
    """Save (or request saving) a source to groups, and unsave it from others.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : SourceGroupsPost
        The object and the groups to save it to or unsave it from. At least
        one of ``invite_group_ids`` or ``unsave_group_ids`` must be
        non-empty. Groups the current user can access are saved immediately
        (``active``); the others are recorded as save requests
        (``requested``), pending approval by a member of that group.
    """
    unwrap(
        client.post(
            "/api/source_groups",
            json=payload.model_dump(by_alias=True, exclude_none=True),
        )
    )


def update_source_group(
    client: httpx.Client,
    obj_id: str,
    group_id: int,
    *,
    active: bool,
    requested: bool,
) -> None:
    """Update the saved/requested state of a source within one group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source, e.g. ``"ZTF20abcdef"``.
    group_id : int
        ID of the group whose save record is being updated. The source must
        already have a record for this group.
    active : bool
        Whether the source is saved to the group. Flipping this from false
        to true records the current user as the saver.
    requested : bool
        Whether the source is still requested to be saved to the group.
    """
    payload: dict[str, int | bool] = {
        "groupID": group_id,
        "active": active,
        "requested": requested,
    }
    unwrap(client.patch(f"/api/source_groups/{obj_id}", json=payload))
