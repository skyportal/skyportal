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


class AnnotationPostBody(BaseModel):
    """Request body for posting an annotation."""

    # Clients still send handler-derived fields (obj_id) that the previous
    # marshmallow schema silently ignored; ignore rather than reject them.
    model_config = ConfigDict(extra="ignore")

    origin: str = Field(
        pattern=r"^\w+",
        description="String describing the source of this information. "
        "Only one Annotation per origin is allowed, although each Annotation "
        "can have multiple fields. To add/change data, use the update method "
        "instead of trying to post another Annotation from this origin. "
        "Origin must be a non-empty string starting with an alphanumeric "
        "character or underscore (it must match the regex: /^\\w+/).",
    )
    data: dict[str, Any] = Field(description="Annotation data as {key: value} pairs.")
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view annotation. Defaults to all of requesting user's groups.",
    )


class AnnotationPostResponse(BaseModel):
    """Data payload returned when posting an annotation."""

    annotation_id: int = Field(description="New annotation ID")


class AnnotationPutBody(BaseModel):
    """Request body for updating an annotation."""

    # Clients still send handler-derived fields (obj_id, author_id) that the
    # previous marshmallow schema silently ignored; ignore rather than reject.
    model_config = ConfigDict(extra="ignore")

    data: dict[str, Any] | None = Field(
        default=None, description="Annotation data as {key: value} pairs."
    )
    origin: str | None = Field(
        default=None,
        description="String describing the source of this information.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should "
        "be able to view the annotation.",
    )


class IRSAQueryWISEBody(BaseModel):
    """Request body for posting WISE cross-match annotations."""

    model_config = ConfigDict(extra="forbid")

    catalog: str = Field(
        default="allwise_p3as_psd",
        description="The name of the catalog key, associated with a catalog cross "
        "match, from which the data should be retrieved. Default is allwise_p3as_psd.",
    )
    crossmatchRadius: float | None = Field(
        default=2.0,
        description="Crossmatch radius (in arcseconds) to retrieve photoz's. "
        "Default is 2.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be able "
        "to view annotation. Defaults to all of requesting user's groups.",
    )


class VizierQueryBody(BaseModel):
    """Request body for posting Vizier cross-match annotations."""

    model_config = ConfigDict(extra="forbid")

    catalog: str = Field(
        default="VII/290",
        description="The name of the catalog key, associated with a catalog cross "
        "match, from which the data should be retrieved. Default is VII/290.",
    )
    crossmatchRadius: float | None = Field(
        default=2.0,
        description="Crossmatch radius (in arcseconds) to retrieve photoz's. "
        "Default is 2.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be able "
        "to view annotation. Defaults to all of requesting user's groups.",
    )


class DatalabQueryBody(BaseModel):
    """Request body for posting Datalab cross-match annotations."""

    model_config = ConfigDict(extra="forbid")

    catalog: str = Field(
        default="ls_dr10",
        description="The name of the catalog key, associated with a catalog cross "
        "match, from which the photoz data should be retrieved. Default is ls_dr10.",
    )
    crossmatchRadius: float | None = Field(
        default=2.0,
        description="Crossmatch radius (in arcseconds) to retrieve photoz's. "
        "Default is 2.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be able "
        "to view annotation. Defaults to all of requesting user's groups.",
    )


class PS1QueryBody(BaseModel):
    """Request body for posting PS1 cross-match annotations."""

    model_config = ConfigDict(extra="forbid")

    catalog: str = Field(
        default="ps1.dr2",
        description="The name of the catalog key, used when posting annotations. "
        "Default is ps1.dr2. This is not used for the query, which will always query "
        "DR2.",
    )
    crossmatchRadius: float | None = Field(
        default=2.0,
        description="Crossmatch radius (in arcseconds) to retrieve PS1 sources. "
        "Default is 2.",
    )
    crossmatchMinDetections: int | None = Field(
        default=1,
        description="Crossmatch minimum number of detections to retrieve PS1 "
        "sources. Default is 1.",
    )
    crossmatchNumber: int | None = Field(
        default=5,
        description="Crossmatch number of sources (maximum) to retrieve from PS1. "
        "Default is 1, max is 5.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be able "
        "to view annotation. Defaults to all of requesting user's groups.",
    )
