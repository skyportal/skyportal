"""Typed endpoint functions for ``/api/sharing_service``."""

from __future__ import annotations

import httpx
from skyportal_py_models.sharing_services import (
    PhotometryOptions,
    SharingServiceAutoPublishersPostResponse,
    SharingServiceCoauthorPostResponse,
    SharingServiceCoauthorResponse,
    SharingServiceGroupAutoPublisherResponse,
    SharingServiceGroupPutResponse,
    SharingServiceGroupResponse,
    SharingServicePost,
    SharingServicePutResponse,
    SharingServiceResponse,
    SharingServiceSubmissionPost,
    SharingServiceSubmissionResponse,
    SharingServiceSubmissionsPageResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "PhotometryOptions",
    "SharingServiceAutoPublishersPostResponse",
    "SharingServiceCoauthorPostResponse",
    "SharingServiceCoauthorResponse",
    "SharingServiceGroupAutoPublisherResponse",
    "SharingServiceGroupPutResponse",
    "SharingServiceGroupResponse",
    "SharingServicePost",
    "SharingServicePutResponse",
    "SharingServiceResponse",
    "SharingServiceSubmissionPost",
    "SharingServiceSubmissionResponse",
    "SharingServiceSubmissionsPageResponse",
]


def fetch_sharing_services(client: httpx.Client) -> list[SharingServiceResponse]:
    """Retrieve all sharing services visible to the token.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.

    Notes
    -----
    Only services shared with one of the caller's groups are returned,
    unless the caller is a system admin. The TNS credentials
    (``_tns_altdata``) are never included in the response.
    """
    response = client.get("/api/sharing_service")
    return [SharingServiceResponse.model_validate(item) for item in unwrap(response)]


def fetch_sharing_service(
    client: httpx.Client,
    sharing_service_id: int,
) -> SharingServiceResponse:
    """Retrieve a single sharing service by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service.
    """
    response = client.get(f"/api/sharing_service/{sharing_service_id}")
    return SharingServiceResponse.model_validate(unwrap(response))


def post_sharing_service(
    client: httpx.Client,
    payload: SharingServicePost,
) -> SharingServicePutResponse:
    """Create a sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : SharingServicePost
        The service to create. ``name`` must be unique and at least one
        instrument must be given. ``owner_group_ids`` lists the groups that
        will own the service; owner groups are created with all their
        auto-sharing flags off. If ``enable_sharing_with_tns`` is true, then
        ``tns_bot_id``, ``tns_source_group_id`` and a ``tns_altdata``
        containing an ``api_key`` are all required. ``testing`` defaults to
        true server-side, meaning payloads are stored but nothing is
        actually published.
    """
    response = client.put(
        "/api/sharing_service",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return SharingServicePutResponse.model_validate(unwrap(response))


def update_sharing_service(
    client: httpx.Client,
    sharing_service_id: int,
    payload: SharingServicePost,
) -> SharingServicePutResponse:
    """Update an existing sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service to update.
    payload : SharingServicePost
        The new values. Omitted fields are left unchanged, so ``name`` may
        simply repeat the current name. ``owner_group_ids`` is ignored here;
        use :func:`update_sharing_service_group` to change ownership.
        Instruments are only replaced when ``instrument_ids`` is non-empty,
        while ``stream_ids`` always replaces the current streams. Disabling
        TNS or Hermes sharing also clears the matching auto-sharing flags on
        every group of the service.
    """
    response = client.put(
        f"/api/sharing_service/{sharing_service_id}",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return SharingServicePutResponse.model_validate(unwrap(response))


def delete_sharing_service(client: httpx.Client, sharing_service_id: int) -> None:
    """Delete a sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service to delete. Only a member of one of its
        owner groups may delete it.
    """
    unwrap(client.delete(f"/api/sharing_service/{sharing_service_id}"))


def post_sharing_service_submission(
    client: httpx.Client,
    payload: SharingServiceSubmissionPost,
) -> None:
    """Request the publication of an object through a sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : SharingServiceSubmissionPost
        The submission to queue. At least one of ``publish_to_tns`` and
        ``publish_to_hermes`` must be true, ``publishers`` must be a
        non-empty string, and ``archival_comment`` is required when
        ``archival`` is true. Submitting the same object to the same
        destination twice through the same service is rejected. The
        submission is queued and processed asynchronously; poll
        :func:`fetch_sharing_service_submissions` for its status.
    """
    unwrap(
        client.post(
            "/api/sharing_service/submission",
            json=payload.model_dump(exclude_none=True),
        )
    )


def fetch_sharing_service_submission(
    client: httpx.Client,
    sharing_service_submission_id: int,
    *,
    sharing_service_id: int,
) -> SharingServiceSubmissionResponse:
    """Retrieve a single sharing service submission by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_submission_id : int
        ID of the submission.
    sharing_service_id : int
        ID of the sharing service the submission belongs to. Required by
        the endpoint even though the submission ID is unique.
    """
    response = client.get(
        f"/api/sharing_service/submission/{sharing_service_submission_id}",
        params={"sharing_service_id": sharing_service_id},
    )
    return SharingServiceSubmissionResponse.model_validate(unwrap(response))


def fetch_sharing_service_submissions(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    sharing_service_id: int,
    page_number: int = 1,
    num_per_page: int = 100,
    include_payload: bool = False,
    include_response: bool = False,
    object_id: str | None = None,
) -> SharingServiceSubmissionsPageResponse:
    """Query the submissions of a sharing service, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service whose submissions are queried.
    page_number, num_per_page : int, optional
        Pagination controls. Submissions are returned newest first.
    include_payload : bool, optional
        Include the payload sent to TNS, which is deferred by default.
    include_response : bool, optional
        Include the raw response from the external service, which is
        deferred by default.
    object_id : str, optional
        Restrict to submissions of this object.
    """
    params: dict[str, str | int | bool] = {
        "sharing_service_id": sharing_service_id,
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "include_payload": include_payload,
        "include_response": include_response,
    }
    if object_id is not None:
        params["objectID"] = object_id
    response = client.get("/api/sharing_service/submission", params=params)
    return SharingServiceSubmissionsPageResponse.model_validate(unwrap(response))


def post_sharing_service_coauthor(
    client: httpx.Client,
    sharing_service_id: int,
    user_id: int,
) -> SharingServiceCoauthorPostResponse:
    """Add a coauthor to a sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service.
    user_id : int
        ID of the user to credit as a coauthor. The user must have at least
        one affiliation set in their profile and must not be a bot.
    """
    response = client.post(
        f"/api/sharing_service/{sharing_service_id}/coauthor/{user_id}"
    )
    return SharingServiceCoauthorPostResponse.model_validate(unwrap(response))


def delete_sharing_service_coauthor(
    client: httpx.Client,
    sharing_service_id: int,
    user_id: int,
) -> None:
    """Remove a coauthor from a sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service.
    user_id : int
        ID of the user to remove as a coauthor.
    """
    unwrap(
        client.delete(f"/api/sharing_service/{sharing_service_id}/coauthor/{user_id}")
    )


def update_sharing_service_group(  # noqa: PLR0913 -- mirrors the endpoint's request body
    client: httpx.Client,
    sharing_service_id: int,
    group_id: int,
    *,
    owner: bool | None = None,
    auto_share_to_tns: bool | None = None,
    auto_share_to_hermes: bool | None = None,
    auto_sharing_allow_bots: bool | None = None,
) -> SharingServiceGroupPutResponse:
    """Give a group access to a sharing service, or edit its settings.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service.
    group_id : int
        ID of the group to add or edit.
    owner : bool, optional
        Whether the group owns the sharing service. Ownership cannot be
        removed from the only owning group.
    auto_share_to_tns, auto_share_to_hermes : bool, optional
        Whether new sources saved to the group are published automatically.
    auto_sharing_allow_bots : bool, optional
        Whether bot users may act as auto-publishers. It cannot be turned
        off while a bot is still listed as an auto-publisher.

    Notes
    -----
    When the group already has access, at least one of the options must be
    given; otherwise omitted options default to false on the new access.
    """
    payload: dict[str, bool] = {}
    if owner is not None:
        payload["owner"] = owner
    if auto_share_to_tns is not None:
        payload["auto_share_to_tns"] = auto_share_to_tns
    if auto_share_to_hermes is not None:
        payload["auto_share_to_hermes"] = auto_share_to_hermes
    if auto_sharing_allow_bots is not None:
        payload["auto_sharing_allow_bots"] = auto_sharing_allow_bots
    response = client.put(
        f"/api/sharing_service/{sharing_service_id}/group/{group_id}",
        json=payload,
    )
    return SharingServiceGroupPutResponse.model_validate(unwrap(response))


def delete_sharing_service_group(
    client: httpx.Client,
    sharing_service_id: int,
    group_id: int,
) -> None:
    """Remove a group's access to a sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service.
    group_id : int
        ID of the group to remove. The only group owning the service cannot
        be removed; add another owner group first.
    """
    unwrap(client.delete(f"/api/sharing_service/{sharing_service_id}/group/{group_id}"))


def post_sharing_service_auto_publishers(
    client: httpx.Client,
    sharing_service_id: int,
    group_id: int,
    user_ids: list[int],
) -> SharingServiceAutoPublishersPostResponse:
    """Add auto-publishers to a group of a sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service.
    group_id : int
        ID of the group, which must already have access to the service.
    user_ids : list of int
        IDs of the users to add. Each must be a member of the group and
        have at least one affiliation set in their profile. Bot users are
        only accepted when the group has ``auto_sharing_allow_bots`` set.
        The request fails as a whole if any user is rejected.
    """
    response = client.post(
        f"/api/sharing_service/{sharing_service_id}/group/{group_id}/auto_publisher",
        json={"user_ids": user_ids},
    )
    return SharingServiceAutoPublishersPostResponse.model_validate(unwrap(response))


def delete_sharing_service_auto_publishers(
    client: httpx.Client,
    sharing_service_id: int,
    group_id: int,
    user_ids: list[int],
) -> None:
    """Remove auto-publishers from a group of a sharing service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    sharing_service_id : int
        ID of the sharing service.
    group_id : int
        ID of the group.
    user_ids : list of int
        IDs of the users to remove. Each must currently be an
        auto-publisher of the group; the request fails as a whole
        otherwise.
    """
    path = f"/api/sharing_service/{sharing_service_id}/group/{group_id}/auto_publisher"
    unwrap(client.request("DELETE", path, json={"user_ids": user_ids}))
