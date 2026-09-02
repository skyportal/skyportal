"""Typed endpoint functions for ``/api/public_pages``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models.public_pages import (
    PublicReleasePost,
    PublicReleasePostResponse,
    PublicReleaseResponse,
    PublicReleaseUpdate,
    PublicSourcePageOptionsResponse,
    PublicSourcePagePostResponse,
    PublicSourcePageResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "PublicReleasePost",
    "PublicReleasePostResponse",
    "PublicReleaseResponse",
    "PublicReleaseUpdate",
    "PublicSourcePageOptionsResponse",
    "PublicSourcePagePostResponse",
    "PublicSourcePageResponse",
]


def fetch_public_source_pages(
    client: httpx.Client,
    source_id: str,
) -> list[PublicSourcePageResponse]:
    """Retrieve the visible public pages of a source, newest first.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    source_id : str
        Object ID of the source, e.g. ``"ZTF20abcdef"``.
    """
    response = client.get(f"/api/public_pages/source/{source_id}")
    return [PublicSourcePageResponse.model_validate(page) for page in unwrap(response)]


def post_public_source_page(
    client: httpx.Client,
    source_id: str,
    options: dict[str, Any],
    *,
    release_id: int | None = None,
) -> PublicSourcePagePostResponse:
    """Publish a public page for a source.

    The server hashes the published data and rejects the request if a page
    with identical data, options and release already exists. The rendered
    page is only generated when the page has no release or its release is
    visible.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    source_id : str
        Object ID of the source to publish.
    options : dict
        Options controlling what is published. Recognized keys are
        ``"groups"`` and ``"streams"`` (ID lists restricting the data pulled
        in) and the booleans ``"include_summary"``, ``"include_photometry"``,
        ``"include_spectroscopy"`` and ``"include_classifications"``.
    release_id : int, optional
        ID of the public release the page belongs to. Omit for a standalone
        page.
    """
    payload: dict[str, Any] = {"options": options}
    if release_id is not None:
        payload["release_id"] = release_id
    response = client.post(f"/api/public_pages/source/{source_id}", json=payload)
    return PublicSourcePagePostResponse.model_validate(unwrap(response))


def delete_public_source_page(client: httpx.Client, page_id: int) -> None:
    """Delete a public source page and drop it from the page cache.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_id : int
        ID of the public source page to delete.
    """
    unwrap(client.delete(f"/api/public_pages/source/{page_id}"))


def fetch_public_releases(client: httpx.Client) -> list[PublicReleaseResponse]:
    """Retrieve all public releases, ordered by name.

    Each release's ``group_ids`` lists only the owning groups the calling
    user can access.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/public_pages/release")
    return [
        PublicReleaseResponse.model_validate(release) for release in unwrap(response)
    ]


def post_public_release(
    client: httpx.Client,
    payload: PublicReleasePost,
) -> PublicReleasePostResponse:
    """Create a public release.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : PublicReleasePost
        Release name, URL-safe ``link_name`` (alphanumerics, dashes,
        underscores, periods and plus signs only, and unique across
        releases), at least one owning group ID, and optionally a
        description, default source-page ``options``, whether the release is
        visible to the public (default ``True``) and whether sources from the
        same groups are auto-published into it (default ``False``).
    """
    response = client.post(
        "/api/public_pages/release", json=payload.model_dump(exclude_none=True)
    )
    return PublicReleasePostResponse.model_validate(unwrap(response))


def update_public_release(
    client: httpx.Client,
    release_id: int,
    payload: PublicReleaseUpdate,
) -> None:
    """Update a public release.

    The server rewrites every listed field, so omitted optional fields are
    reset to their defaults (empty description, empty options, visible,
    auto-publish disabled) rather than left unchanged. ``link_name`` cannot
    be changed. Making a visible release invisible drops its source pages
    from the page cache.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    release_id : int
        ID of the release to update.
    payload : PublicReleaseUpdate
        New name, owning group IDs, and optionally description, default
        source-page options, public visibility and auto-publishing.
    """
    unwrap(
        client.patch(
            f"/api/public_pages/release/{release_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def delete_public_release(client: httpx.Client, release_id: int) -> None:
    """Delete a public release.

    The release must have no public source pages left in it.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    release_id : int
        ID of the release to delete.
    """
    unwrap(client.delete(f"/api/public_pages/release/{release_id}"))
