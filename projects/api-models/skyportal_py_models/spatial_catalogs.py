"""Response models for ``/api/spatial_catalog``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class SpatialCatalogGetQuery(BaseModel):
    """Query parameters for retrieving spatial catalogs."""

    model_config = ConfigDict(extra="forbid")

    catalog_name: str | None = Field(
        default=None,
        description="Name of the catalog being looked up, reported back in the not-found error message.",
    )


class SpatialCatalogPostBody(BaseModel):
    """Request body for ingesting a spatial catalog."""

    model_config = ConfigDict(extra="forbid")

    catalog_name: Any = Field(default=None, description="Spatial catalog name.")
    catalog_data: Any = Field(default=None, description="Spatial catalog data")


class SpatialCatalogPostResponse(BaseModel):
    """ID of the newly created spatial catalog."""

    id: int = Field(description="New spatial catalog ID")


class SpatialCatalogASCIIFilePostBody(BaseModel):
    """Request body for uploading a spatial catalog from an ASCII file."""

    model_config = ConfigDict(extra="forbid")

    catalogData: str | None = Field(
        default=None, description="Catalog data Ascii string"
    )
    catalogName: str | None = Field(default=None, description="Spatial catalog name.")


class SpatialCatalogASCIIFilePostResponse(BaseModel):
    """ID of the newly created spatial catalog."""

    id: int = Field(description="New spatial catalog ID")
