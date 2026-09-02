"""Typed endpoint functions for ``/api/healpix``."""

from __future__ import annotations

import httpx
from skyportal_py_models.healpix import HealpixCountsResponse, HealpixUpdateResponse

from skyportal_py._http import unwrap

__all__ = [
    "HealpixCountsResponse",
    "HealpixUpdateResponse",
]


def fetch_healpix_counts(client: httpx.Client) -> HealpixCountsResponse:
    """Count the objects with and without a HEALPix index.

    Requires the ``System admin`` ACL.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/healpix")
    return HealpixCountsResponse.model_validate(unwrap(response))


def post_healpix_update(
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 100,
) -> HealpixUpdateResponse:
    """Compute HEALPix indices for one batch of objects that lack them.

    Requires the ``System admin`` ACL. ``total_matches`` in the response
    counts the objects still missing a HEALPix index before this batch ran.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls; the server defaults to page 1 and 100 per page,
        and caps ``num_per_page`` at 500.
    """
    params = {"pageNumber": page_number, "numPerPage": num_per_page}
    response = client.post("/api/healpix", params=params)
    return HealpixUpdateResponse.model_validate(unwrap(response))
