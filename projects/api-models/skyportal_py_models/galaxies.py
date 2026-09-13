"""Response models for ``/api/galaxy_catalog``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GalaxyResponse(BaseModel):
    """A galaxy from a galaxy catalog (a ``Galaxy`` row)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    catalog_id: int | None = None
    name: str | None = None
    alt_name: str | None = None
    ra: float | None = None
    dec: float | None = None
    healpix: int | None = None
    distmpc: float | None = None
    distmpc_unc: float | None = None
    redshift: float | None = None
    redshift_error: float | None = None
    sfr_fuv: float | None = None
    sfr_w4: float | None = None
    mstar: float | None = None
    magb: float | None = None
    magk: float | None = None
    mag_fuv: float | None = None
    mag_nuv: float | None = None
    mag_w1: float | None = None
    mag_w2: float | None = None
    mag_w3: float | None = None
    mag_w4: float | None = None
    a: float | None = None
    b2a: float | None = None
    pa: float | None = None
    btc: float | None = None
    # typed as dict to avoid an import cycle with sources
    objects: list[dict[str, Any]] | None = None
    # Injected by the handler when ``returnProbability`` is requested.
    probability: float | None = None


class GalaxiesPageResponse(BaseModel):
    """One page of results from a galaxy catalog query."""

    # Hand-built by the handler, which strips keys whose value is ``None``, so
    # ``sortBy``/``sortOrder`` are absent unless they were requested and
    # ``geojson`` is only present when ``includeGeoJSON`` was set.

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    galaxies: list[GalaxyResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)
    sort_by: str | None = Field(alias="sortBy", default=None)
    sort_order: str | None = Field(alias="sortOrder", default=None)
    page: int | None = None
    num_per_page: int | None = Field(alias="numPerPage", default=None)
    geojson: dict[str, Any] | None = None


class GalaxyCatalogCountResponse(BaseModel):
    """A galaxy catalog name with its galaxy count."""

    # Hand-built by the handler from a ``GalaxyCatalog`` plus a count of its
    # galaxies; the catalog's description and URL are not returned.

    model_config = ConfigDict(extra="forbid")

    catalog_name: str
    catalog_count: int | None = None
