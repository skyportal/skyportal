"""Response models for classifications."""

from __future__ import annotations

from datetime import date
from typing import ClassVar

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


DEFAULT_CLASSIFICATIONS_PER_PAGE = 100


class ClassificationPostItem(BaseModel):
    """A single classification. Cross-field checks (probability range, allowed
    classes, ml value) are enforced by the handler with their own messages."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(default=None, description="ID of the object.")
    classification: str | None = Field(default=None, description="The assigned class.")
    origin: str | None = Field(
        default=None, description="String describing the source of this classification."
    )
    taxonomy_id: int | None = Field(
        default=None, description="ID of the taxonomy the classification is from."
    )
    probability: float | None = Field(
        default=None,
        description="User-assigned probability of this classification on this "
        "taxonomy. If multiple classifications are given for the same source by "
        "the same user, the sum of the classifications ought to equal unity. Only "
        "individual probabilities are checked.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view classification. Defaults to the public group.",
    )
    vote: bool | None = Field(
        default=None, description="Add vote associated with classification."
    )
    label: bool | None = Field(
        default=None, description="Add label associated with classification."
    )
    ml: bool | str | None = Field(
        default=None, description="Whether this is a machine-learning classification."
    )


class ClassificationPostBody(ClassificationPostItem):
    """Request body for posting a classification. Either a single classification
    (top-level fields) or a batch (a list under `classifications`)."""

    classifications: list[ClassificationPostItem] | None = Field(
        default=None,
        description="List of classifications to post in a single request. If "
        "provided, the top-level single-classification fields are ignored.",
    )


class ClassificationPutBody(BaseModel):
    """Request body for updating a classification."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(default=None, description="ID of the object.")
    classification: str | None = Field(default=None, description="The assigned class.")
    origin: str | None = Field(
        default=None, description="String describing the source of this classification."
    )
    taxonomy_id: int | None = Field(
        default=None, description="ID of the taxonomy the classification is from."
    )
    probability: float | None = Field(
        default=None,
        description="User-assigned probability of this classification on this "
        "taxonomy.",
    )
    ml: bool | str | None = Field(
        default=None, description="Whether this is a machine-learning classification."
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view classification.",
    )


class ClassificationDeleteBody(BaseModel):
    """Request body for deleting classification(s)."""

    model_config = ConfigDict(extra="forbid")

    label: bool = Field(
        default=True, description="Add label associated with classification."
    )


class ClassificationVotePostBody(BaseModel):
    """Request body for voting on a classification."""

    model_config = ConfigDict(extra="forbid")

    vote: int | None = Field(
        default=None, description="Upvote or downvote a classification."
    )


class ClassificationGetQuery(BaseModel):
    """Query parameters for retrieving classifications."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"includeTaxonomy"})

    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "filter by created_at >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "filter by created_at <= endDate"
        ),
    )
    includeTaxonomy: bool = Field(
        default=False,
        description="Return associated taxonomy.",
    )
    numPerPage: int = Field(
        default=DEFAULT_CLASSIFICATIONS_PER_PAGE,
        description="Number of sources to return per paginated request. Defaults to 100. Max 500.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1",
    )


class ObjClassificationGetQuery(BaseModel):
    """Query parameters for retrieving an object's classifications."""

    model_config = ConfigDict(extra="forbid")

    includeSuperObjs: bool = Field(
        default=False,
        description=(
            "If true and the obj is linked to other objs via a SuperObj "
            "(meta-object), return the union of classifications across all "
            "linked objs. Each entry carries its obj_id for provenance."
        ),
    )


class ObjClassificationQueryGetQuery(BaseModel):
    """Query parameters for finding sources with classifications."""

    model_config = ConfigDict(extra="forbid")

    startDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01) for when the "
            "classification was made. If provided, filter by created_at >= startDate"
        ),
    )
    endDate: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01) for when the "
            "classification was made. If provided, filter by created_at <= endDate"
        ),
    )


__all__ = [
    "DEFAULT_CLASSIFICATIONS_PER_PAGE",
    "ClassificationPostItem",
    "ClassificationPostBody",
    "ClassificationPutBody",
    "ClassificationDeleteBody",
    "ClassificationVotePostBody",
    "ClassificationGetQuery",
    "ObjClassificationGetQuery",
    "ObjClassificationQueryGetQuery",
    "ClassificationPost",
    "ClassificationUpdate",
    "ClassificationEditResponse",
    "ClassificationPostResponse",
    "ClassificationResponse",
    "ClassificationVoteResponse",
    "ClassificationsPageResponse",
    "ClassificationsPostResponse",
]
