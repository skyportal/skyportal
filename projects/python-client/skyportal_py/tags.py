"""Typed endpoint functions for ``/api/objtagoption`` and ``/api/objtag``."""

from __future__ import annotations

import httpx
from skyportal_py_models.candidates import ObjTagResponse
from skyportal_py_models.tags import ObjTagOptionResponse, ObjTagPostResponse

from skyportal_py._http import unwrap

__all__ = [
    "ObjTagOptionResponse",
    "ObjTagPostResponse",
    "ObjTagResponse",
]


def fetch_obj_tag_options(client: httpx.Client) -> list[ObjTagOptionResponse]:
    """Retrieve all available tag options.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/objtagoption")
    return [ObjTagOptionResponse.model_validate(item) for item in unwrap(response)]


def post_obj_tag_option(
    client: httpx.Client,
    name: str,
    *,
    color: str | None = None,
) -> ObjTagOptionResponse:
    """Create a new tag option.

    Requires the "Manage sources" permission. Names are unique
    case-insensitively.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str
        Tag name; letters and numbers only.
    color : str, optional
        Hex color code for display, e.g. ``"#3a87ad"``.
    """
    payload: dict[str, str] = {"name": name}
    if color is not None:
        payload["color"] = color
    response = client.post("/api/objtagoption", json=payload)
    return ObjTagOptionResponse.model_validate(unwrap(response))


def update_obj_tag_option(
    client: httpx.Client,
    tag_id: int,
    name: str,
    *,
    color: str | None = None,
) -> None:
    """Update an existing tag option's name and/or color.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    tag_id : int
        ID of the tag option to update.
    name : str
        New tag name; letters and numbers only.
    color : str, optional
        New hex color code, e.g. ``"#3a87ad"``. If omitted, the color is
        left unchanged.
    """
    payload: dict[str, str] = {"name": name}
    if color is not None:
        payload["color"] = color
    unwrap(client.patch(f"/api/objtagoption/{tag_id}", json=payload))


def delete_obj_tag_option(client: httpx.Client, tag_id: int) -> None:
    """Delete a tag option.

    Requires the "Manage sources" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    tag_id : int
        ID of the tag option to delete.
    """
    unwrap(client.delete(f"/api/objtagoption/{tag_id}"))


def fetch_obj_tags(
    client: httpx.Client,
    *,
    obj_id: str | None = None,
    objtagoption_id: int | None = None,
    include_super_objs: bool = False,
) -> list[ObjTagResponse]:
    """Retrieve object-tag associations, optionally filtered.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str, optional
        Restrict to associations on this object.
    objtagoption_id : int, optional
        Restrict to associations of this tag option.
    include_super_objs : bool, optional
        If True and ``obj_id`` is given, also return tags on the objects
        linked to it through a super-object; each entry keeps its own
        ``obj_id``. Defaults to False.
    """
    params: dict[str, str | int | bool] = {}
    if obj_id is not None:
        params["obj_id"] = obj_id
    if objtagoption_id is not None:
        params["objtagoption_id"] = objtagoption_id
    if include_super_objs:
        params["includeSuperObjs"] = True
    response = client.get("/api/objtag", params=params)
    return [ObjTagResponse.model_validate(item) for item in unwrap(response)]


def post_obj_tag(
    client: httpx.Client,
    obj_id: str,
    objtagoption_id: int,
    *,
    group_ids: list[int] | None = None,
) -> ObjTagPostResponse:
    """Tag an object by creating an object-tag association.

    If the association already exists, the server instead adds the given
    groups to it and returns only ``id`` and ``message`` (or an empty
    result if there was nothing to add).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        ID of the object to tag.
    objtagoption_id : int
        ID of the tag option to associate.
    group_ids : list of int, optional
        Groups that can access this tag association. Defaults to the
        server's public group.
    """
    payload: dict[str, str | int | list[int]] = {
        "obj_id": obj_id,
        "objtagoption_id": objtagoption_id,
    }
    if group_ids is not None:
        payload["group_ids"] = group_ids
    response = client.post("/api/objtag", json=payload)
    return ObjTagPostResponse.model_validate(unwrap(response) or {})


def delete_obj_tag(
    client: httpx.Client,
    association_id: int,
    *,
    group_ids: list[int] | None = None,
) -> None:
    """Remove group associations from an object tag.

    If ``group_ids`` is provided, only those groups are removed;
    otherwise all of the user's group associations are removed. If no
    group associations remain afterwards, the tag itself is deleted.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    association_id : int
        ID of the object-tag association.
    group_ids : list of int, optional
        GroupResponse IDs to remove; must be non-empty if provided.
    """
    payload: dict[str, list[int]] = {}
    if group_ids is not None:
        payload["group_ids"] = group_ids
    unwrap(client.request("DELETE", f"/api/objtag/{association_id}", json=payload))
