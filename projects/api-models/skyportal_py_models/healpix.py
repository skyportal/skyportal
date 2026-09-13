"""Response models for ``/api/healpix``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealpixCountsResponse(BaseModel):
    """Counts of objects with and without a HEALPix index."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    total_without_healpix: int = Field(alias="totalWithoutHealpix", default=0)
    total_with_healpix: int = Field(alias="totalWithHealpix", default=0)


class HealpixUpdateResponse(BaseModel):
    """Result of a HEALPix backfill batch.

    ``total_matches`` counts the objects still missing a HEALPix index before
    the batch ran.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    total_matches: int = Field(alias="totalMatches", default=0)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)
