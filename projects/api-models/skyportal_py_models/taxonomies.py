"""Response models for ``/api/taxonomy``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import TaxonomyResponse


class TaxonomyPost(BaseModel):
    """Payload for creating a taxonomy."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    name: str
    version: str
    hierarchy: dict[str, Any] | None = None
    hierarchy_file: str | None = None
    group_ids: list[int] | None = None
    provenance: str | None = None
    is_latest: bool = Field(alias="isLatest", default=True)


class TaxonomyPut(BaseModel):
    """Payload for updating a taxonomy."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    name: str | None = None
    version: str | None = None
    provenance: str | None = None
    is_latest: bool | None = Field(alias="isLatest", default=None)
    group_ids: list[int] | None = None


class TaxonomyPostBody(BaseModel):
    """Request body for posting a new taxonomy."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Short string to make this taxonomy memorable to end users."
    )
    version: str = Field(description="Semantic version of this taxonomy name")
    hierarchy: dict[str, Any] | None = Field(
        default=None,
        description="Nested JSON describing the taxonomy which should be "
        "validated against a schema before entry. One of `hierarchy` or "
        "`hierarchy_file` must be provided.",
    )
    hierarchy_file: str | None = Field(
        default=None,
        description="YAML string describing the taxonomy, parsed into "
        "`hierarchy` when provided.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should "
        "be able to view the taxonomy. Defaults to the public group.",
    )
    provenance: str | None = Field(
        default=None,
        description="Identifier (e.g., URL or git hash) that uniquely ties "
        "this taxonomy back to an origin or place of record",
    )
    isLatest: bool = Field(
        default=True,
        description="Consider this version of the taxonomy with this name "
        "the latest? Defaults to True.",
    )


class TaxonomyPostResponse(BaseModel):
    """Data payload returned when posting a taxonomy."""

    taxonomy_id: int = Field(description="New taxonomy ID")


class TaxonomyPutBody(BaseModel):
    """Request body for updating a taxonomy."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        description="Short string to make this taxonomy memorable to end users.",
    )
    version: str | None = Field(
        default=None, description="Semantic version of this taxonomy name"
    )
    provenance: str | None = Field(
        default=None,
        description="Identifier (e.g., URL or git hash) that uniquely ties "
        "this taxonomy back to an origin or place of record",
    )
    isLatest: bool | None = Field(
        default=None,
        description="Consider this version of the taxonomy with this name the latest?",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should "
        "be able to view the taxonomy.",
    )
    hierarchy: dict[str, Any] | None = Field(
        default=None,
        description="Not editable; upload a new taxonomy if a hierarchy "
        "change is desired.",
    )


__all__ = [
    "TaxonomyPostBody",
    "TaxonomyPostResponse",
    "TaxonomyPutBody",
    "TaxonomyPost",
    "TaxonomyPut",
    "TaxonomyResponse",
]
