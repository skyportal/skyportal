"""Typed endpoint functions for ``/api/invitations``."""

from __future__ import annotations

import httpx
from skyportal_py_models.invitations import (
    InvitationPost,
    InvitationPostResponse,
    InvitationResponse,
    InvitationsPageResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "InvitationPost",
    "InvitationPostResponse",
    "InvitationResponse",
    "InvitationsPageResponse",
]


def fetch_invitations(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 25,
    include_used: bool | None = None,
    email: str | None = None,
    group: str | None = None,
    stream: str | None = None,
    invited_by: str | None = None,
) -> InvitationsPageResponse:
    """Query invitations, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls; the server defaults to 25 per page.
    include_used : bool, optional
        Also return invitations that have already been accepted. Defaults to
        false server-side, i.e. only pending invitations are returned.
    email : str, optional
        Substring match on the invited email address.
    group : str, optional
        Only invitations to the group with this exact name.
    stream : str, optional
        Only invitations granting access to the stream with this exact name.
    invited_by : str, optional
        Substring match on the username of the inviting user.
    """
    params: dict[str, str | int | bool] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if include_used is not None:
        params["includeUsed"] = include_used
    if email is not None:
        params["email"] = email
    if group is not None:
        params["group"] = group
    if stream is not None:
        params["stream"] = stream
    if invited_by is not None:
        params["invitedBy"] = invited_by
    response = client.get("/api/invitations", params=params)
    return InvitationsPageResponse.model_validate(unwrap(response))


def post_invitation(
    client: httpx.Client,
    payload: InvitationPost,
) -> InvitationPostResponse:
    """Invite a new user by email.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : InvitationPost
        The invitation to create. ``role`` must be either ``"Full user"`` or
        ``"View only"`` and defaults to ``"Full user"``. If ``stream_ids`` is
        omitted the user is granted access to every stream associated with
        the invited groups; if given, it must cover those streams.
        ``group_admin``, ``can_save`` and ``can_share_photometry`` are
        per-group flags and must be the same length as ``group_ids``; they
        default to all false, all true, and all false respectively. The
        endpoint errors unless invitations are enabled in the deployment's
        configuration.
    """
    response = client.post(
        "/api/invitations",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return InvitationPostResponse.model_validate(unwrap(response))


def update_invitation(  # noqa: PLR0913 -- mirrors the endpoint's request body
    client: httpx.Client,
    invitation_id: int,
    *,
    group_ids: list[int] | None = None,
    stream_ids: list[int] | None = None,
    role: str | None = None,
    user_expiration_date: str | None = None,
) -> None:
    """Update a pending invitation.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    invitation_id : int
        ID of the invitation to update. Only the inviting user may update it.
    group_ids : list of int, optional
        Replacement list of groups the invited user will join.
    stream_ids : list of int, optional
        Replacement list of streams the invited user will access. The
        resulting streams must cover every stream of the invited groups.
    role : str, optional
        New role, either ``"Full user"`` or ``"View only"``.
    user_expiration_date : str, optional
        Arrow-parseable date after which the new account is deactivated.
    """
    payload: dict[str, str | list[int]] = {}
    if group_ids is not None:
        payload["groupIDs"] = group_ids
    if stream_ids is not None:
        payload["streamIDs"] = stream_ids
    if role is not None:
        payload["role"] = role
    if user_expiration_date is not None:
        payload["userExpirationDate"] = user_expiration_date
    unwrap(client.patch(f"/api/invitations/{invitation_id}", json=payload))


def delete_invitation(client: httpx.Client, invitation_id: int) -> None:
    """Delete an invitation.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    invitation_id : int
        ID of the invitation to delete. Only the inviting user may delete it.
    """
    unwrap(client.delete(f"/api/invitations/{invitation_id}"))
