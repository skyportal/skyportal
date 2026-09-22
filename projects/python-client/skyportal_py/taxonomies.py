"""Typed endpoint functions for ``/api/taxonomy``."""

from __future__ import annotations

import httpx
from skyportal_py_models._cyclic import TaxonomyResponse
from skyportal_py_models.taxonomies import (
    TaxonomyPost,
    TaxonomyPostResponse,
    TaxonomyPut,
)

from skyportal_py._http import unwrap

__all__ = [
    "TaxonomyPost",
    "TaxonomyPostResponse",
    "TaxonomyPut",
    "TaxonomyResponse",
]


def fetch_taxonomies(client: httpx.Client) -> list[TaxonomyResponse]:
    """Retrieve the taxonomies usable by the token's groups.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/taxonomy")
    return [TaxonomyResponse.model_validate(item) for item in unwrap(response)]


def fetch_taxonomy(client: httpx.Client, taxonomy_id: int) -> TaxonomyResponse:
    """Retrieve a single taxonomy by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    taxonomy_id : int
        ID of the taxonomy.
    """
    response = client.get(f"/api/taxonomy/{taxonomy_id}")
    return TaxonomyResponse.model_validate(unwrap(response))


def post_taxonomy(
    client: httpx.Client,
    payload: TaxonomyPost,
) -> TaxonomyPostResponse:
    """Create a taxonomy.

    Exactly one of ``hierarchy`` (nested JSON) or ``hierarchy_file`` (the
    same structure as a YAML string) must be given, and the hierarchy is
    validated against the ``tdtax`` schema. The name/version combination
    must not already exist. ``group_ids`` defaults to the public group, and
    any group the token cannot access is dropped. When ``is_latest`` is true
    every other taxonomy with the same name is marked not-latest. Requires
    the "Post taxonomy" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : TaxonomyPost
        The taxonomy to create.
    """
    response = client.post(
        "/api/taxonomy", json=payload.model_dump(exclude_none=True, by_alias=True)
    )
    return TaxonomyPostResponse.model_validate(unwrap(response))


def update_taxonomy(
    client: httpx.Client,
    taxonomy_id: int,
    payload: TaxonomyPut,
) -> None:
    """Update a taxonomy.

    Only the provided fields are sent; omitted fields are left unchanged.
    The hierarchy cannot be edited: post a new taxonomy instead. Groups the
    token cannot access are dropped from ``group_ids``. Requires the
    "Post taxonomy" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    taxonomy_id : int
        ID of the taxonomy to update.
    payload : TaxonomyPut
        The fields to change.
    """
    unwrap(
        client.put(
            f"/api/taxonomy/{taxonomy_id}",
            json=payload.model_dump(exclude_none=True, by_alias=True),
        )
    )


def delete_taxonomy(client: httpx.Client, taxonomy_id: int) -> None:
    """Delete a taxonomy.

    Fails if any classification still references the taxonomy. Requires the
    "Delete taxonomy" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    taxonomy_id : int
        ID of the taxonomy to delete.
    """
    unwrap(client.delete(f"/api/taxonomy/{taxonomy_id}"))
