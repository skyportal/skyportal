"""Typed endpoint functions for source comments."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models._cyclic import CommentResponse
from skyportal_py_models.comments import (
    CommentAttachment,
    CommentAttachmentBatchResponse,
    CommentAttachmentCountsResponse,
    CommentDetailResponse,
    CommentPostResponse,
)

from skyportal_py._http import unwrap, unwrap_content

__all__ = [
    "CommentAttachment",
    "CommentAttachmentBatchResponse",
    "CommentAttachmentCountsResponse",
    "CommentDetailResponse",
    "CommentPostResponse",
    "CommentResponse",
]


def fetch_comments(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    resource_id: str | int,
    *,
    resource_type: str = "sources",
    text: str | None = None,
    channel: str | None = None,
    page_number: int = 1,
    num_per_page: int = 25,
) -> list[CommentResponse]:
    """Retrieve the comments on a commentable resource.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the commented resource: an object ID for sources, otherwise
        an integer ID.
    resource_type : str, optional
        What the comments are on: ``"sources"`` (the default),
        ``"spectra"``, ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    text : str, optional
        Restrict to comments whose text contains this string; matching
        comments come back newest first.
    channel : str, optional
        Restrict to source comments on this channel. Only applies when
        ``resource_type`` is ``"sources"``; without it the server returns
        only channel-less comments.
    page_number, num_per_page : int, optional
        Pagination controls; the server caps the page size and only
        paginates when ``text`` is provided.
    """
    params: dict[str, str | int] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if text is not None:
        params["text"] = text
    if channel is not None:
        params["channel"] = channel
    response = client.get(f"/api/{resource_type}/{resource_id}/comments", params=params)
    return [CommentResponse.model_validate(comment) for comment in unwrap(response)]


def post_comment(
    client: httpx.Client,
    resource_id: str | int,
    text: str,
    *,
    resource_type: str = "sources",
    group_ids: list[int] | None = None,
) -> CommentPostResponse:
    """Post a comment on a commentable resource.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the resource to comment on: an object ID for sources,
        otherwise an integer ID.
    text : str
        The comment text.
    resource_type : str, optional
        What to comment on: ``"sources"`` (the default), ``"spectra"``,
        ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    group_ids : list of int, optional
        Restrict the comment's visibility to these groups. If omitted, the
        server applies its default visibility.
    """
    payload: dict[str, str | list[int]] = {"text": text}
    if group_ids is not None:
        payload["group_ids"] = group_ids
    response = client.post(f"/api/{resource_type}/{resource_id}/comments", json=payload)
    return CommentPostResponse.model_validate(unwrap(response))


def update_comment(  # noqa: PLR0913 -- mirrors the request body
    client: httpx.Client,
    resource_id: str | int,
    comment_id: int,
    text: str | None = None,
    *,
    resource_type: str = "sources",
    attachment_name: str | None = None,
    attachment_body: str | None = None,
    group_ids: list[int] | None = None,
) -> None:
    """Update a comment on a commentable resource.

    Omitted fields are left unchanged; provide at least one. To replace the
    attachment, give ``attachment_name`` and ``attachment_body`` together.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the commented resource: an object ID for sources, otherwise
        an integer ID.
    comment_id : int
        ID of the comment to update.
    text : str, optional
        The new comment text.
    resource_type : str, optional
        What the comment is on: ``"sources"`` (the default), ``"spectra"``,
        ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    attachment_name : str, optional
        Filename of the replacement attachment.
    attachment_body : str, optional
        Base64-encoded contents of the replacement attachment, optionally
        still carrying a ``data:...;base64,`` prefix.
    group_ids : list of int, optional
        Restrict the comment's visibility to these groups. If omitted, the
        visibility is left unchanged.
    """
    payload: dict[str, Any] = {}
    if text is not None:
        payload["text"] = text
    if attachment_name is not None or attachment_body is not None:
        payload["attachment"] = {"name": attachment_name, "body": attachment_body}
    if group_ids is not None:
        payload["group_ids"] = group_ids
    unwrap(
        client.put(
            f"/api/{resource_type}/{resource_id}/comments/{comment_id}", json=payload
        )
    )


def delete_comment(
    client: httpx.Client,
    resource_id: str | int,
    comment_id: int,
    *,
    resource_type: str = "sources",
) -> None:
    """Delete a comment on a commentable resource.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the commented resource: an object ID for sources, otherwise
        an integer ID.
    comment_id : int
        ID of the comment to delete.
    resource_type : str, optional
        What the comment is on: ``"sources"`` (the default), ``"spectra"``,
        ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    """
    unwrap(client.delete(f"/api/{resource_type}/{resource_id}/comments/{comment_id}"))


def fetch_comment(
    client: httpx.Client,
    resource_id: str | int,
    comment_id: int,
    *,
    resource_type: str = "sources",
) -> CommentDetailResponse:
    """Retrieve a single comment on any commentable resource.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the commented resource: an object ID for sources, otherwise
        an integer ID. It must match the comment's own resource.
    comment_id : int
        ID of the comment.
    resource_type : str, optional
        What the comment is on: ``"sources"`` (the default), ``"spectra"``,
        ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    """
    response = client.get(f"/api/{resource_type}/{resource_id}/comments/{comment_id}")
    return CommentDetailResponse.model_validate(unwrap(response))


def post_comment_with_attachment(  # noqa: PLR0913 -- mirrors the request body
    client: httpx.Client,
    resource_id: str | int,
    text: str,
    attachment_name: str,
    attachment_body: str,
    *,
    resource_type: str = "sources",
    group_ids: list[int] | None = None,
) -> CommentPostResponse:
    """Post a comment carrying a file attachment.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the resource to comment on: an object ID for sources,
        otherwise an integer ID.
    text : str
        The comment text.
    attachment_name : str
        Filename of the attachment; its extension decides whether the
        server can render a preview later.
    attachment_body : str
        Base64-encoded file contents, optionally still carrying a
        ``data:...;base64,`` prefix.
    resource_type : str, optional
        What to comment on: ``"sources"`` (the default), ``"spectra"``,
        ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    group_ids : list of int, optional
        Restrict the comment's visibility to these groups. If omitted, the
        comment goes to the public group. Comments posted with a token are
        flagged as bot comments.
    """
    payload: dict[str, Any] = {
        "text": text,
        "attachment": {"name": attachment_name, "body": attachment_body},
    }
    if group_ids is not None:
        payload["group_ids"] = group_ids
    response = client.post(f"/api/{resource_type}/{resource_id}/comments", json=payload)
    return CommentPostResponse.model_validate(unwrap(response))


def fetch_comment_attachment(
    client: httpx.Client,
    resource_id: str | int,
    comment_id: int,
    *,
    resource_type: str = "sources",
    preview: bool = False,
) -> bytes:
    """Download a comment's attachment as raw bytes.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the commented resource; it must match the comment's own
        resource.
    comment_id : int
        ID of the comment holding the attachment.
    resource_type : str, optional
        What the comment is on: ``"sources"`` (the default), ``"spectra"``,
        ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    preview : bool, optional
        Return a renderable preview instead of the raw file: FITS files
        come back as PNG, and other types must be in the server's list of
        previewable extensions.
    """
    params: dict[str, str] = (
        {"download": "", "preview": "true"} if preview else {"download": "true"}
    )
    response = client.get(
        f"/api/{resource_type}/{resource_id}/comments/{comment_id}/attachment",
        params=params,
    )
    return unwrap_content(response)


def fetch_comment_attachment_pdf(
    client: httpx.Client,
    resource_id: str | int,
    comment_id: int,
    *,
    resource_type: str = "sources",
    preview: bool = False,
) -> bytes:
    """Download a comment's attachment from the ``.pdf`` alias route.

    This serves exactly the same bytes as
    :func:`fetch_comment_attachment`; the suffixed URL exists only so that
    PDF viewers which key off the file extension can load it.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the commented resource; it must match the comment's own
        resource.
    comment_id : int
        ID of the comment holding the attachment.
    resource_type : str, optional
        What the comment is on: ``"sources"`` (the default), ``"spectra"``,
        ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    preview : bool, optional
        Return the attachment inline rather than as a download.
    """
    params: dict[str, str] = (
        {"download": "", "preview": "true"} if preview else {"download": "true"}
    )
    response = client.get(
        f"/api/{resource_type}/{resource_id}/comments/{comment_id}/attachment.pdf",
        params=params,
    )
    return unwrap_content(response)


def fetch_comment_attachment_text(
    client: httpx.Client,
    resource_id: str | int,
    comment_id: int,
    *,
    resource_type: str = "sources",
) -> CommentAttachment:
    """Retrieve a comment's attachment decoded as text.

    Only useful for text-like attachments; binary files raise a decoding
    error on the server. Use :func:`fetch_comment_attachment` otherwise.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    resource_id : str or int
        ID of the commented resource; it must match the comment's own
        resource.
    comment_id : int
        ID of the comment holding the attachment.
    resource_type : str, optional
        What the comment is on: ``"sources"`` (the default), ``"spectra"``,
        ``"gcn_event"``, ``"shift"`` or ``"earthquake"``.
    """
    response = client.get(
        f"/api/{resource_type}/{resource_id}/comments/{comment_id}/attachment",
        params={"download": "", "preview": ""},
    )
    return CommentAttachment.model_validate(unwrap(response))


def fetch_comment_attachment_counts(
    client: httpx.Client,
) -> CommentAttachmentCountsResponse:
    """Count comments whose attachment is still stored in the database.

    Requires the System admin ACL.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/comment_attachment")
    return CommentAttachmentCountsResponse.model_validate(unwrap(response))


def post_comment_attachment_batch(
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 100,
) -> CommentAttachmentBatchResponse:
    """Move one page of in-database comment attachments onto disk.

    Requires the System admin ACL. Because migrated comments drop out of
    the result set, repeated calls with ``page_number=1`` walk the whole
    backlog.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls over the comments that still hold attachment
        bytes. ``num_per_page`` is capped at 500 by the server.
    """
    response = client.post(
        "/api/comment_attachment",
        params={"pageNumber": page_number, "numPerPage": num_per_page},
    )
    return CommentAttachmentBatchResponse.model_validate(unwrap(response))
