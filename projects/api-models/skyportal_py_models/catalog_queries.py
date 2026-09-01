"""Request models for ``/api/catalog_queries``."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class CatalogQueryPostBody(BaseModel):
    """Request body for submitting a catalog query."""

    model_config = ConfigDict(extra="forbid")

    allocation_id: int = Field(description="Catalog query request allocation ID.")
    payload: dict[str, Any] | None = Field(
        default=None, description="Content of the catalog query request."
    )
    status: str | None = Field(default=None, description="The status of the request.")
    target_group_ids: list[int] | None = Field(
        default=None,
        description="IDs of groups to share the results of the query with.",
    )


class SwiftLSXPSQueryPostBody(BaseModel):
    """Request body for posting Swift LSXPS objects as sources."""

    model_config = ConfigDict(extra="forbid")

    telescope_name: str | None = Field(
        default=None,
        description="Name of telescope to assign this catalog to. Use the same "
        "name as your nickname for the Neil Gehrels Swift Observatory. Defaults "
        "to Swift.",
    )
    groupIDs: list[int] | None = Field(
        default=None, description="If provided, save to these group IDs."
    )


class GaiaPhotometricAlertsQueryPostBody(BaseModel):
    """Request body for posting Gaia Photometric Alerts as sources."""

    model_config = ConfigDict(extra="forbid")

    telescope_name: str | None = Field(
        default=None,
        description="Name of telescope to assign this catalog to. Use the same "
        "name as your nickname for Gaia. Defaults to Gaia.",
    )
    groupIDs: list[int] | None = Field(
        default=None, description="If provided, save to these group IDs."
    )
    startDate: str | None = Field(
        default=None, description="Arrow parsable string. Filter by start date."
    )
    endDate: str | None = Field(
        default=None, description="Arrow parsable string. Filter by end date."
    )


class TessTransientsQueryPostBody(BaseModel):
    """Request body for posting TESS transients as sources."""

    model_config = ConfigDict(extra="forbid")

    telescope_name: str | None = Field(
        default=None,
        description="Name of telescope to assign this catalog to. Use the same "
        "name as your nickname for TESS. Defaults to TESS.",
    )
    groupIDs: list[int] | None = Field(
        default=None, description="If provided, save to these group IDs."
    )
    startDate: str | None = Field(
        default=None, description="Arrow parsable string. Filter by start date."
    )
    endDate: str | None = Field(
        default=None, description="Arrow parsable string. Filter by end date."
    )
