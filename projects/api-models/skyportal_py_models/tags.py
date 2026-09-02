"""Response models for ``/api/objtagoption`` and ``/api/objtag``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse


class ObjTagOptionResponse(BaseModel):
    """A tag that can be applied to objects."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    color: str | None = None


class ObjTagResponse(BaseModel):
    """An object-tag association.

    Handlers that assemble the payload by hand add name (the tag option's
    name) and, on the internal endpoints, total_group_count.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    objtagoption_id: int | None = None
    author_id: int | None = None
    objtagoption: ObjTagOptionResponse | None = None
    groups: list[GroupResponse] | None = None
    # the package has no model for a bare Obj, and author is a partial user
    # projection rather than a full UserResponse
    obj: dict[str, Any] | None = None
    author: dict[str, Any] | None = None
    name: str | None = None
    total_group_count: int | None = None


class ObjTagPostResponse(BaseModel):
    """Result of creating an object-tag association.

    A brand-new association comes back in full; adding groups to one that
    already exists returns only id and message, and adding nothing returns
    an empty result.
    """

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    objtagoption_id: int | None = None
    author_id: int | None = None
    groups: list[dict[str, Any]] | None = None
    message: str | None = None


class ObjTagOptionPostBody(BaseModel):
    """Request body for creating a tag option."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Tag name (letters and numbers only)")
    color: str | None = Field(
        default=None, description="Hex color code (e.g., #3a87ad)"
    )


class ObjTagOptionPatchBody(BaseModel):
    """Request body for updating a tag option."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="New tag name")
    color: str | None = Field(
        default=None, description="New hex color code (e.g., #3a87ad)"
    )


class ObjTagGetQuery(BaseModel):
    """Query parameters for listing object-tag associations."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(
        default=None, description="Filter associations by object ID"
    )
    objtagoption_id: int | None = Field(
        default=None, description="Filter associations by tag option ID"
    )
    includeSuperObjs: bool = Field(
        default=False,
        description="If true and obj_id is given, also return tags on the Objs "
        "linked to it through a SuperObj (meta-object), as one provenance-tagged "
        "union (each entry keeps its obj_id). Defaults to false.",
    )


class ObjTagPostBody(BaseModel):
    """Request body for creating an object-tag association."""

    model_config = ConfigDict(extra="forbid")

    objtagoption_id: int = Field(description="ID of the tag option to associate")
    obj_id: str = Field(description="ID of the object to tag")
    group_ids: list[int] | None = Field(
        default=None,
        description="IDs of groups that can access this tag association. "
        "Defaults to the public group.",
    )


class ObjTagDeleteBody(BaseModel):
    """Request body for removing group associations from an object-tag
    association."""

    model_config = ConfigDict(extra="forbid")

    group_ids: list[int] | None = Field(
        default=None,
        description="Optional list of group IDs to remove. If not provided, "
        "all user's group associations are removed.",
    )
