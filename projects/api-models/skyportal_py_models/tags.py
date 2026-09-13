"""Response models for ``/api/objtagoption`` and ``/api/objtag``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

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
