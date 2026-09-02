"""Typed endpoint functions for ``/api/thumbnail``."""

from __future__ import annotations

import httpx
from skyportal_py_models.candidates import ThumbnailResponse
from skyportal_py_models.thumbnails import (
    ThumbnailPathReportResponse,
    ThumbnailPost,
    ThumbnailPostResponse,
    ThumbnailType,
)

from skyportal_py._http import unwrap

__all__ = [
    "ThumbnailPathReportResponse",
    "ThumbnailPost",
    "ThumbnailPostResponse",
    "ThumbnailResponse",
    "ThumbnailType",
]

"""ThumbnailResponse types SkyPortal accepts (upstream ``THUMBNAIL_TYPES``)."""


def fetch_thumbnail(client: httpx.Client, thumbnail_id: int) -> ThumbnailResponse:
    """Retrieve a single thumbnail by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    thumbnail_id : int
        ID of the thumbnail.
    """
    response = client.get(f"/api/thumbnail/{thumbnail_id}")
    return ThumbnailResponse.model_validate(unwrap(response))


def post_thumbnail(
    client: httpx.Client,
    payload: ThumbnailPost,
) -> ThumbnailPostResponse:
    """Upload a thumbnail for an object.

    The server decodes the image, writes it under ``static/thumbnails`` and
    rejects anything that is not a PNG between 16 and 500 pixels on a side.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ThumbnailPost
        Object ID, base64-encoded PNG contents, thumbnail type (one of
        ``"new"``, ``"ref"``, ``"sub"``, ``"sdss"``, ``"dr8"``, ``"new_gz"``,
        ``"ref_gz"``, ``"sub_gz"``) and optionally the survey the cutout came
        from (``None`` for all-sky archival thumbnails).
    """
    response = client.post("/api/thumbnail", json=payload.model_dump(exclude_none=True))
    return ThumbnailPostResponse.model_validate(unwrap(response))


def update_thumbnail(  # noqa: PLR0913 -- mirrors the endpoint's body parameters
    client: httpx.Client,
    thumbnail_id: int,
    *,
    obj_id: str | None = None,
    type: ThumbnailType | None = None,  # noqa: A002 -- mirrors the field name
    file_uri: str | None = None,
    public_url: str | None = None,
    origin: str | None = None,
    is_grayscale: bool | None = None,
) -> None:
    """Update fields of an existing thumbnail.

    Only the provided fields are sent; omitted fields are left unchanged.
    The image file itself is not moved or rewritten.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    thumbnail_id : int
        ID of the thumbnail to update.
    obj_id : str, optional
        New object ID the thumbnail belongs to.
    type : str, optional
        New thumbnail type, e.g. ``"ref"``, ``"new"``, ``"sub"``.
    file_uri : str, optional
        New path of the thumbnail on the machine running SkyPortal.
    public_url : str, optional
        New publicly accessible URL of the thumbnail.
    origin : str, optional
        New origin of the thumbnail.
    is_grayscale : bool, optional
        Whether the thumbnail is (mostly) grayscale.
    """
    fields = {
        "obj_id": obj_id,
        "type": type,
        "file_uri": file_uri,
        "public_url": public_url,
        "origin": origin,
        "is_grayscale": is_grayscale,
    }
    payload = {name: value for name, value in fields.items() if value is not None}
    unwrap(client.put(f"/api/thumbnail/{thumbnail_id}", json=payload))


def delete_thumbnail(client: httpx.Client, thumbnail_id: int) -> None:
    """Delete a thumbnail.

    The image file on disk is removed along with the database row.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    thumbnail_id : int
        ID of the thumbnail to delete.
    """
    unwrap(client.delete(f"/api/thumbnail/{thumbnail_id}"))


def fetch_thumbnail_paths(
    client: httpx.Client,
    *,
    types: list[str] | None = None,
    required_depth: int | None = None,
) -> ThumbnailPathReportResponse:
    """Count thumbnails stored in the correct and incorrect folders.

    Requires the ``System admin`` ACL. Nothing is moved; this only reports.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    types : list of str, optional
        ThumbnailResponse types to check. The server defaults to
        ``["new", "ref", "sub"]``, the types stored locally.
    required_depth : int, optional
        Number of hashed subdirectories thumbnails are expected to live in,
        between 0 and 32. The server default is 2.
    """
    params: dict[str, list[str] | int] = {}
    if types is not None:
        params["types"] = types
    if required_depth is not None:
        params["requiredDepth"] = required_depth
    response = client.get("/api/thumbnailPath", params=params)
    return ThumbnailPathReportResponse.model_validate(unwrap(response))


def update_thumbnail_paths(
    client: httpx.Client,
    *,
    types: list[str] | None = None,
    required_depth: int | None = None,
    num_per_page: int | None = None,
    page_number: int | None = None,
) -> ThumbnailPathReportResponse:
    """Move thumbnails that are in the wrong folder and fix their database rows.

    Requires the ``System admin`` ACL. Files are moved on disk and their
    ``file_uri`` and ``public_url`` updated; thumbnails whose file is missing
    are dropped and re-fetched from the alert broker. Only one page of
    thumbnails is processed per call, so repeat until nothing is left in the
    wrong folder.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    types : list of str, optional
        ThumbnailResponse types to check. The server defaults to
        ``["new", "ref", "sub"]``.
    required_depth : int, optional
        Number of hashed subdirectories thumbnails should live in, between 1
        and 32. The server default is 2.
    num_per_page : int, optional
        Number of thumbnails to process. Defaults to 100, capped at 1000.
    page_number : int, optional
        Page to process. Defaults to 1.
    """
    params: dict[str, list[str] | int] = {}
    if types is not None:
        params["types"] = types
    if required_depth is not None:
        params["requiredDepth"] = required_depth
    if num_per_page is not None:
        params["numPerPage"] = num_per_page
    if page_number is not None:
        params["pageNumber"] = page_number
    response = client.patch("/api/thumbnailPath", params=params)
    return ThumbnailPathReportResponse.model_validate(unwrap(response))


def delete_thumbnail_folders(client: httpx.Client) -> None:
    """Delete every empty subfolder under the thumbnails directory.

    Requires the ``System admin`` ACL. These folders are left behind after
    thumbnails are moved to a different folder structure.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    unwrap(client.delete("/api/thumbnailPath"))
