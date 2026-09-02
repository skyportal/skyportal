"""Typed endpoint functions for ``/api/groups``."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import (
    GroupMemberResponse,
    GroupResponse,
    GroupUserResponse,
)
from skyportal_py_models.groups import (
    GroupPost,
    GroupPostResponse,
    GroupsResponse,
    GroupStreamPostResponse,
    GroupUserPostResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "GroupMemberResponse",
    "GroupPost",
    "GroupPostResponse",
    "GroupResponse",
    "GroupStreamPostResponse",
    "GroupUserPostResponse",
    "GroupUserResponse",
    "GroupsResponse",
]


def fetch_groups(
    client: httpx.Client,
    *,
    include_single_user_groups: bool = False,
) -> GroupsResponse:
    """Retrieve the groups the token's user belongs to or can access.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    include_single_user_groups : bool, optional
        Also include each user's implicit single-user group.
    """
    response = client.get(
        "/api/groups",
        params={"includeSingleUserGroups": include_single_user_groups},
    )
    return GroupsResponse.model_validate(unwrap(response))


def fetch_group(
    client: httpx.Client,
    group_id: int,
    *,
    include_group_users: bool = True,
) -> GroupResponse:
    """Retrieve a single group by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group.
    include_group_users : bool, optional
        Include the group's members in ``users``. On by default; pass False
        to skip the member list on large groups.
    """
    response = client.get(
        f"/api/groups/{group_id}",
        params={"includeGroupUsers": include_group_users},
    )
    return GroupResponse.model_validate(unwrap(response))


def fetch_groups_by_name(client: httpx.Client, name: str) -> list[GroupResponse]:
    """Retrieve the accessible groups with an exact name.

    The ``name=`` form of ``GET /api/groups`` returns a plain list rather
    than the user/accessible split of :func:`fetch_groups`.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str
        Exact group name to match.
    """
    response = client.get("/api/groups", params={"name": name})
    return [GroupResponse.model_validate(group) for group in unwrap(response)]


def post_group(client: httpx.Client, payload: GroupPost) -> GroupPostResponse:
    """Create a new group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : GroupPost
        The group to create. ``name`` must not collide with an existing
        group. ``group_admins`` lists user IDs to make group admins; the
        current user is added as an admin automatically.
    """
    response = client.post("/api/groups", json=payload.model_dump(exclude_none=True))
    return GroupPostResponse.model_validate(unwrap(response))


def update_group(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    group_id: int,
    name: str,
    *,
    nickname: str | None = None,
    description: str | None = None,
    private: bool | None = None,
    auto_accept_requests: bool | None = None,
) -> None:
    """Update an existing group.

    Only the provided fields are sent; omitted fields are left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group to update.
    name : str
        The group name; required by the server even if unchanged.
    nickname, description : str, optional
        New nickname and description.
    private : bool, optional
        Whether the group is private.
    auto_accept_requests : bool, optional
        Whether admission requests to the group are accepted automatically.
    """
    fields = {
        "nickname": nickname,
        "description": description,
        "private": private,
        "auto_accept_requests": auto_accept_requests,
    }
    payload: dict[str, str | bool] = {"name": name}
    payload.update({key: value for key, value in fields.items() if value is not None})
    unwrap(client.put(f"/api/groups/{group_id}", json=payload))


def delete_group(client: httpx.Client, group_id: int) -> None:
    """Delete a group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group to delete.
    """
    unwrap(client.delete(f"/api/groups/{group_id}"))


def fetch_public_group(client: httpx.Client) -> GroupResponse:
    """Retrieve the server's configured public group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/groups/public")
    return GroupResponse.model_validate(unwrap(response))


def post_group_stream(
    client: httpx.Client,
    group_id: int,
    stream_id: int,
) -> GroupStreamPostResponse:
    """Grant a group access to an alert stream.

    Every member of the group must already have access to the stream.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group.
    stream_id : int
        ID of the stream to associate with the group.
    """
    response = client.post(
        f"/api/groups/{group_id}/streams", json={"stream_id": stream_id}
    )
    return GroupStreamPostResponse.model_validate(unwrap(response))


def delete_group_stream(client: httpx.Client, group_id: int, stream_id: int) -> None:
    """Remove an alert stream from a group.

    Fails if one of the group's filters still operates on the stream.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group.
    stream_id : int
        ID of the stream to remove from the group.
    """
    unwrap(client.delete(f"/api/groups/{group_id}/streams/{stream_id}"))


def post_group_user(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    group_id: int,
    user_id: int,
    *,
    admin: bool = False,
    can_save: bool = True,
    can_share_photometry: bool = False,
) -> GroupUserPostResponse:
    """Add a user to a group.

    The user must already have access to every stream of the group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group.
    user_id : int
        ID of the user to add.
    admin : bool, optional
        Make the user a group admin.
    can_save : bool, optional
        Allow the user to save sources to the group.
    can_share_photometry : bool, optional
        Allow the user to share the group's photometry with other groups.
    """
    response = client.post(
        f"/api/groups/{group_id}/users",
        json={
            "userID": user_id,
            "admin": admin,
            "canSave": can_save,
            "canSharePhotometry": can_share_photometry,
        },
    )
    return GroupUserPostResponse.model_validate(unwrap(response))


def update_group_user(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    group_id: int,
    user_id: int,
    *,
    admin: bool | None = None,
    can_save: bool | None = None,
    can_share_photometry: bool | None = None,
) -> None:
    """Update a group member's admin or save-access status.

    At least one of ``admin``, ``can_save``, or ``can_share_photometry``
    must be provided; omitted flags are left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group.
    user_id : int
        ID of the group member to update.
    admin : bool, optional
        Whether the user is a group admin.
    can_save : bool, optional
        Whether the user can save sources to the group.
    can_share_photometry : bool, optional
        Whether the user can share the group's photometry with other groups.
    """
    fields = {
        "admin": admin,
        "canSave": can_save,
        "canSharePhotometry": can_share_photometry,
    }
    payload: dict[str, int | bool] = {"userID": user_id}
    payload.update({key: value for key, value in fields.items() if value is not None})
    unwrap(client.patch(f"/api/groups/{group_id}/users", json=payload))


def delete_group_user(client: httpx.Client, group_id: int, user_id: int) -> None:
    """Remove a user from a group.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group.
    user_id : int
        ID of the group member to remove.
    """
    unwrap(client.delete(f"/api/groups/{group_id}/users/{user_id}"))


def post_group_users_from_groups(
    client: httpx.Client,
    group_id: int,
    from_group_ids: list[int],
) -> None:
    """Add all members of other groups to the specified group.

    Users already in the target group are skipped.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int
        ID of the group to add users to.
    from_group_ids : list of int
        IDs of the groups whose members should be added.
    """
    unwrap(
        client.post(
            f"/api/groups/{group_id}/usersFromGroups",
            json={"fromGroupIDs": from_group_ids},
        )
    )
