"""Response models for classifications."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models._cyclic import (
    ClassificationEditResponse,
    ClassificationResponse,
    ClassificationVoteResponse,
)


class ClassificationPostResponse(BaseModel):
    """Result of posting a classification."""

    model_config = ConfigDict(extra="forbid")

    classification_id: int


class ClassificationsPostResponse(BaseModel):
    """Result of posting a batch of classifications."""

    model_config = ConfigDict(extra="forbid")

    classification_ids: list[int] = Field(default_factory=list)


class ClassificationsPageResponse(BaseModel):
    """One page of results from a classifications query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    classifications: list[ClassificationResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)


class ClassificationPost(BaseModel):
    """Payload for posting a classification."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    classification: str
    taxonomy_id: int
    origin: str | None = None
    probability: float | None = None
    ml: bool | None = None
    group_ids: list[int] | None = None
    vote: bool | None = None
    label: bool | None = None


class ClassificationUpdate(BaseModel):
    """Payload for updating a classification."""

    model_config = ConfigDict(extra="forbid")

    classification: str | None = None
    taxonomy_id: int | None = None
    probability: float | None = None
    origin: str | None = None
    ml: bool | None = None
    group_ids: list[int] | None = None


__all__ = [
    "ClassificationPost",
    "ClassificationUpdate",
    "ClassificationEditResponse",
    "ClassificationPostResponse",
    "ClassificationResponse",
    "ClassificationVoteResponse",
    "ClassificationsPageResponse",
    "ClassificationsPostResponse",
]
