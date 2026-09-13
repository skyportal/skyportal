"""Response models for source annotations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse


class AnnotationResponse(BaseModel):
    """An annotation on a source, spectrum, or photometry point.

    Union of the Annotation, AnnotationOnSpectrum, and AnnotationOnPhotometry
    payloads, so each type-specific foreign key is optional.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    origin: str | None = None
    author_id: int | None = None
    author: dict[str, Any] | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    obj_id: str | None = None
    spectrum_id: int | None = None
    photometry_id: int | None = None
    # the package has no model for a bare Obj, and the modules that model the
    # other resources import this one
    obj: dict[str, Any] | None = None
    spectrum: dict[str, Any] | None = None
    photometry: dict[str, Any] | None = None
    type: str | None = None


class AnnotationDetailResponse(AnnotationResponse):
    """A single annotation, as returned by the single-annotation endpoint."""
