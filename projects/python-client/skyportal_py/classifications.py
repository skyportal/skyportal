"""Typed endpoint functions for classifications."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import (
    ClassificationEditResponse,
    ClassificationResponse,
    ClassificationVoteResponse,
)
from skyportal_py_models.classifications import (
    ClassificationPost,
    ClassificationPostResponse,
    ClassificationsPageResponse,
    ClassificationsPostResponse,
    ClassificationUpdate,
)

from skyportal_py._http import unwrap

__all__ = [
    "ClassificationEditResponse",
    "ClassificationPost",
    "ClassificationPostResponse",
    "ClassificationResponse",
    "ClassificationUpdate",
    "ClassificationVoteResponse",
    "ClassificationsPageResponse",
    "ClassificationsPostResponse",
]


def fetch_classifications(
    client: httpx.Client,
    obj_id: str,
    *,
    include_super_objs: bool = False,
) -> list[ClassificationResponse]:
    """Retrieve the classifications of a source.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source, e.g. ``"ZTF20abcdef"``.
    include_super_objs : bool, optional
        Aggregate classifications from every object linked through the
        source's SuperObjResponse.
    """
    response = client.get(
        f"/api/sources/{obj_id}/classifications",
        params={"includeSuperObjs": include_super_objs},
    )
    return [ClassificationResponse.model_validate(item) for item in unwrap(response)]


def post_classification(
    client: httpx.Client,
    payload: ClassificationPost,
) -> ClassificationPostResponse:
    """Post a classification of a source.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ClassificationPost
        The classification to post. ``classification`` must be a class in
        the taxonomy identified by ``taxonomy_id``. If ``group_ids`` is
        omitted, the server applies its default visibility.
    """
    response = client.post(
        "/api/classification", json=payload.model_dump(exclude_none=True)
    )
    return ClassificationPostResponse.model_validate(unwrap(response))


def post_classifications(
    client: httpx.Client,
    payloads: list[ClassificationPost],
) -> ClassificationsPostResponse:
    """Post several classifications in one request.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payloads : list of ClassificationPost
        The classifications to post; same semantics as
        :func:`post_classification`, applied per entry.
    """
    response = client.post(
        "/api/classification",
        json={
            "classifications": [
                payload.model_dump(exclude_none=True) for payload in payloads
            ]
        },
    )
    return ClassificationsPostResponse.model_validate(unwrap(response))


def delete_classification(client: httpx.Client, classification_id: int) -> None:
    """Delete a classification.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    classification_id : int
        ID of the classification to delete.
    """
    unwrap(client.delete(f"/api/classification/{classification_id}"))


def fetch_classification(
    client: httpx.Client,
    classification_id: int,
    *,
    include_taxonomy: bool = False,
) -> ClassificationResponse:
    """Retrieve a single classification by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    classification_id : int
        ID of the classification.
    include_taxonomy : bool, optional
        Include the associated taxonomy in the response.
    """
    response = client.get(
        f"/api/classification/{classification_id}",
        params={"includeTaxonomy": include_taxonomy},
    )
    return ClassificationResponse.model_validate(unwrap(response))


def fetch_classifications_query(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 100,
    start_date: str | None = None,
    end_date: str | None = None,
    include_taxonomy: bool = False,
) -> ClassificationsPageResponse:
    """Query all accessible classifications, one page at a time.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls. ``num_per_page`` defaults to 100 and is
        capped server-side at 500.
    start_date, end_date : str, optional
        Restrict to classifications created in this date range, as
        ISO-format date strings, e.g. ``"2020-01-01"``.
    include_taxonomy : bool, optional
        Include each classification's associated taxonomy.
    """
    params: dict[str, str | int | bool] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "includeTaxonomy": include_taxonomy,
    }
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    response = client.get("/api/classification", params=params)
    return ClassificationsPageResponse.model_validate(unwrap(response))


def update_classification(
    client: httpx.Client,
    classification_id: int,
    payload: ClassificationUpdate,
) -> None:
    """Update a classification.

    Only the provided fields are sent. Note that the server treats an
    omitted ``ml`` flag as ``False``, so pass ``ml=True`` on every update
    of a machine-learning classification to preserve it.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    classification_id : int
        ID of the classification to update.
    payload : ClassificationUpdate
        The fields to change. If ``group_ids`` is provided, it replaces
        the set of groups that can view the classification.
    """
    unwrap(
        client.put(
            f"/api/classification/{classification_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def delete_source_classifications(
    client: httpx.Client,
    obj_id: str,
    *,
    label: bool | None = None,
) -> None:
    """Delete all of a source's classifications.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source whose classifications are deleted.
    label : bool, optional
        Whether to also record a source label for the deleting user in
        each affected group. The server defaults to ``True``.
    """
    path = f"/api/sources/{obj_id}/classifications"
    if label is None:
        unwrap(client.request("DELETE", path))
    else:
        unwrap(client.request("DELETE", path, json={"label": label}))


def post_classification_vote(
    client: httpx.Client,
    classification_id: int,
    vote: int,
) -> None:
    """Vote on a classification.

    A user has at most one vote per classification; voting again
    overwrites the previous vote.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    classification_id : int
        ID of the classification to vote on.
    vote : int
        The vote value, generally ``1`` (upvote) or ``-1`` (downvote).
    """
    unwrap(
        client.post(
            f"/api/classification/votes/{classification_id}",
            json={"vote": vote},
        )
    )


def delete_classification_vote(
    client: httpx.Client,
    classification_id: int,
) -> None:
    """Delete the token user's vote on a classification.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    classification_id : int
        ID of the classification whose vote is removed.
    """
    unwrap(client.delete(f"/api/classification/votes/{classification_id}"))


def fetch_sources_by_classification(
    client: httpx.Client,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[str]:
    """Retrieve the object IDs of sources that have classifications.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    start_date, end_date : str, optional
        Restrict to classifications created in this date range, as
        ISO-format date strings, e.g. ``"2020-01-01"``.
    """
    params: dict[str, str] = {}
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    response = client.get("/api/classification/sources", params=params)
    return list(unwrap(response))
