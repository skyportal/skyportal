"""Request models for ``/api/catalog_queries``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class CatalogQueryPost(BaseModel):
    """Payload for submitting a catalog query."""

    # ``requester_id`` is filled in server-side from the token's user. The
    # created ``CatalogQuery`` is not returned here; it is read back through
    # the GCN event's catalog queries.

    model_config = ConfigDict(extra="forbid")

    allocation_id: int
    payload: dict[str, Any]
    status: str | None = None
    target_group_ids: list[int] | None = None
