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


__all__ = [
    "TaxonomyPost",
    "TaxonomyPut",
    "TaxonomyResponse",
]
