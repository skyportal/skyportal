"""Response models for ``/api/galaxy_catalog``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class GalaxyCatalogPost(BaseModel):
    """Payload for ingesting a galaxy catalog."""

    # The upstream OpenAPI schema documents ``catalog_data`` as a list of
    # dicts, but the handler indexes it by column name, so it is really a dict
    # of equal-length column lists.

    model_config = ConfigDict(extra="forbid")

    catalog_name: str
    catalog_data: dict[str, list[Any]]
    catalog_description: str | None = None
    catalog_url: str | None = None

    @field_validator("catalog_data")
    @classmethod
    def _decode_bytes(cls, value: dict[str, list[Any]]) -> dict[str, list[Any]]:
        # HDF5-read tables carry numpy bytes in string columns, which the
        # JSON encoder rejects; decode them the way simplejson used to.
        return {
            column: [
                entry.decode() if isinstance(entry, bytes | bytearray) else entry
                for entry in entries
            ]
            for column, entries in value.items()
        }


class GalaxyCatalogASCIIPost(BaseModel):
    """Payload for uploading a galaxy catalog from an ASCII file."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    catalog_name: str = Field(alias="catalogName")
    catalog_data: str = Field(alias="catalogData")
    catalog_description: str | None = Field(alias="catalogDescription", default=None)
    catalog_url: str | None = Field(alias="catalogURL", default=None)


MAX_GALAXIES = 10000


class GalaxyCatalogPostBody(BaseModel):
    """Request body for ingesting a galaxy catalog."""

    model_config = ConfigDict(extra="forbid")

    catalog_name: str | None = Field(default=None, description="Galaxy catalog name.")
    catalog_description: str | None = Field(
        default=None, description="Galaxy catalog description."
    )
    catalog_url: str | None = Field(default=None, description="Galaxy catalog URL.")
    catalog_data: dict[str, Any] | None = Field(
        default=None,
        description="Galaxy catalog data as a mapping of column name to list of "
        "values (must include ra, dec, and name).",
    )


class GalaxyASCIIFilePostBody(BaseModel):
    """Request body for uploading galaxies from an ASCII file."""

    model_config = ConfigDict(extra="forbid")

    catalogName: str | None = Field(default=None, description="Galaxy catalog name.")
    catalogDescription: str | None = Field(
        default=None, description="Galaxy catalog description."
    )
    catalogURL: str | None = Field(default=None, description="Galaxy catalog URL.")
    catalogData: str | None = Field(
        default=None, description="Catalog data ASCII string."
    )


class GalaxyCatalogFitsPostBody(BaseModel):
    """Request body for uploading galaxies from a FITS catalog."""

    model_config = ConfigDict(extra="forbid")

    file_name: str | None = Field(
        default=None,
        description="Name of the .fits file containing the galaxies (in the data "
        "directory).",
    )
    file_url: str | None = Field(
        default=None,
        description="URL of the .fits file containing the galaxies.",
    )


class ObjHostPostBody(BaseModel):
    """Request body for setting an object's host galaxy."""

    model_config = ConfigDict(extra="forbid")

    galaxyName: str | None = Field(
        default=None, description="Name of the galaxy to associate with the object."
    )


class GalaxyCatalogGetQuery(BaseModel):
    """Query parameters for retrieving galaxies."""

    model_config = ConfigDict(extra="forbid")

    catalog_name: str | None = Field(
        default=None,
        description="Filter by catalog name (exact match)",
    )
    ra: str | None = Field(
        default=None,
        description="RA for spatial filtering (in decimal degrees)",
    )
    dec: str | None = Field(
        default=None,
        description="Declination for spatial filtering (in decimal degrees)",
    )
    radius: str | None = Field(
        default=None,
        description="Radius for spatial filtering if ra & dec are provided (in decimal degrees)",
    )
    galaxyName: str | None = Field(
        default=None,
        description="Portion of name to filter on",
    )
    minDistance: float | None = Field(
        default=None,
        description="If provided, return only galaxies with a distance of at least this value",
    )
    maxDistance: float | None = Field(
        default=None,
        description="If provided, return only galaxies with a distance of at most this value",
    )
    minRedshift: float | None = Field(
        default=None,
        description="If provided, return only galaxies with a redshift of at least this value",
    )
    maxRedshift: float | None = Field(
        default=None,
        description="If provided, return only galaxies with a redshift of at most this value",
    )
    minMstar: float | None = Field(
        default=None,
        description="If provided, return only galaxies with a stellar mass of at least this value",
    )
    maxMstar: float | None = Field(
        default=None,
        description="If provided, return only galaxies with a stellar mass of at most this value",
    )
    localizationDateobs: str | None = Field(
        default=None,
        description="Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).",
    )
    localizationName: str | None = Field(
        default=None,
        description="Name of localization / skymap to use. Can be found in Localization.localization_name queried from /api/localization endopoint or skymap name in GcnEvent page table.",
    )
    localizationCumprob: float = Field(
        default=0.95,
        description="Cumulative probability up to which to include galaxies",
    )
    includeGeoJSON: bool = Field(
        default=False,
        description="Boolean indicating whether to include associated GeoJSON. Defaults to false.",
    )
    numPerPage: int = Field(
        default=1000,
        description=f"Number of galaxies to return per paginated request. Defaults to 1000. Can be no larger than {MAX_GALAXIES}.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1",
    )
    catalogNamesOnly: bool = Field(
        default=False,
        description="Boolean indicating whether to just return catalog names. Defaults to false.",
    )
    returnProbability: bool = Field(
        default=False,
        description="Boolean indicating whether to return probability density. Defaults to false.",
    )
    sortBy: str | None = Field(
        default=None,
        description=(
            "Column to sort by. Can be one of the following: "
            "distmpc, redshift, name, mstar, prob, mstar_prob_weighted, sfr_fuv, magb, magk. "
            "Defaults to no sorting unless a localization and catalog are provided, then defaults to mstar_prob_weighted."
        ),
    )
    sortOrder: str | None = Field(
        default=None,
        description=(
            "Sort order. Can be one of the following: asc, desc. "
            "Defaults to None unless a localization and catalog are provided, then defaults to desc."
        ),
    )
