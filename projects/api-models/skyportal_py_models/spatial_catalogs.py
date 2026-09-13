"""Response models for ``/api/spatial_catalog``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SpatialCatalogEntryResponse(BaseModel):
    """An entry in a spatial catalog (a ``SpatialCatalogEntry``)."""

    # ``uniq`` and ``probdensity`` are deferred columns, so they are absent
    # unless a query explicitly undefers them. The ``catalog`` back-reference
    # is never populated by a load, so it is not declared.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    catalog_id: int | None = None
    entry_name: str | None = None
    # The cone (``ra``, ``dec``, ``radius``) or ellipse (``ra``, ``dec``,
    # ``amaj``, ``amin``, ``phi``) the entry's skymap was generated from.
    data: dict[str, Any] | None = None
    uniq: list[int] | None = None
    probdensity: list[float] | None = None


class SpatialCatalogResponse(BaseModel):
    """A spatial catalog of skymap regions (a ``SpatialCatalog``)."""

    # ``entries`` is only populated by the single-catalog endpoint, and
    # ``entries_count`` is injected only by the list endpoint.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    catalog_name: str | None = None
    entries: list[SpatialCatalogEntryResponse] | None = None
    entries_count: int | None = None
