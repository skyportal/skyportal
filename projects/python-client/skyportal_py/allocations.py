"""Typed endpoint functions for ``/api/allocation``."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import AllocationResponse, AllocationUserResponse
from skyportal_py_models.allocations import (
    AllocationPost,
    AllocationPostResponse,
    AllocationUpdate,
)

from skyportal_py._http import unwrap, unwrap_content

__all__ = [
    "AllocationPost",
    "AllocationPostResponse",
    "AllocationResponse",
    "AllocationUpdate",
    "AllocationUserResponse",
]


def fetch_allocations(
    client: httpx.Client,
    *,
    instrument_id: int | None = None,
    api_type: str | None = None,
    api_implements: str | None = None,
) -> list[AllocationResponse]:
    """Retrieve the allocations visible to the token.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int, optional
        Restrict to allocations on this instrument.
    api_type : str, optional
        Restrict to allocations whose instrument has the given API type
        set: ``"api_classname"`` or ``"api_classname_obsplan"``.
    api_implements : str, optional
        Restrict to allocations whose instrument API implements this
        method, e.g. ``"submit"`` or ``"retrieve"``. Requires
        ``api_type``.
    """
    params: dict[str, str | int] = {}
    if instrument_id is not None:
        params["instrument_id"] = instrument_id
    if api_type is not None:
        params["apiType"] = api_type
    if api_implements is not None:
        params["apiImplements"] = api_implements
    response = client.get("/api/allocation", params=params)
    return [AllocationResponse.model_validate(item) for item in unwrap(response)]


def fetch_allocation(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    allocation_id: int,
    *,
    page_number: int = 1,
    num_per_page: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "asc",
) -> AllocationResponse:
    """Retrieve a single allocation by ID.

    The response embeds the allocation's follow-up requests in
    ``requests``; the pagination and sort parameters apply to that list.
    (The wire response also carries the total request count in a
    ``totalMatches`` sibling key, which this function drops.)

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation.
    page_number, num_per_page : int, optional
        Pagination controls over ``requests``; the server caps the page
        size.
    sort_by : str, optional
        Field to sort ``requests`` by; one of ``"created_at"``,
        ``"modified"``, ``"status"`` or ``"obj"``.
    sort_order : str, optional
        ``"asc"`` or ``"desc"``.
    """
    params: dict[str, str | int] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    response = client.get(f"/api/allocation/{allocation_id}", params=params)
    return AllocationResponse.model_validate(unwrap(response)["allocation"])


def post_allocation(
    client: httpx.Client,
    payload: AllocationPost,
) -> AllocationPostResponse:
    """Create an allocation on a robotic instrument.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : AllocationPost
        The allocation to create. ``altdata`` holds the instrument API
        credentials and is validated by the instrument's API class when it
        implements ``validate_altdata``. ``allocation_admin_ids`` lists the
        users allowed to administer the allocation. Requires the
        ``Manage allocations`` permission.
    """
    response = client.post(
        "/api/allocation",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return AllocationPostResponse.model_validate(unwrap(response))


def update_allocation(
    client: httpx.Client,
    allocation_id: int,
    payload: AllocationUpdate,
) -> None:
    """Update an allocation.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation to update.
    payload : AllocationUpdate
        Fields to change. ``altdata`` is merged into the stored value
        rather than replacing it. ``allocation_admin_ids`` is authoritative:
        any admin not listed is removed, so omitting it clears them all.
        Requires the ``Manage allocations`` permission.
    """
    unwrap(
        client.put(
            f"/api/allocation/{allocation_id}",
            json=payload.model_dump(by_alias=True, exclude_none=True),
        )
    )


def delete_allocation(client: httpx.Client, allocation_id: int) -> None:
    """Delete an allocation.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    allocation_id : int
        ID of the allocation to delete. Requires the ``Manage allocations``
        permission.
    """
    unwrap(client.delete(f"/api/allocation/{allocation_id}"))


def fetch_allocation_report(
    client: httpx.Client,
    instrument_id: int,
    *,
    output_format: str | None = None,
) -> bytes:
    """Retrieve a plotted report on an instrument's allocations.

    The report charts allocated hours, requests made, requests completed and
    the moon-phase distribution of completed requests, per allocation.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_id : int
        ID of the instrument to report on. The server errors unless it has
        at least one accessible allocation.
    output_format : str, optional
        ``"pdf"`` (the server default) or ``"png"``.

    Returns
    -------
    bytes
        The raw report file.
    """
    params = {} if output_format is None else {"output_format": output_format}
    response = client.get(f"/api/allocation/report/{instrument_id}", params=params)
    return unwrap_content(response)
