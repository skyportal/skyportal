"""Models for embedding similarity search over sources."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SimilarSourcesGetQuery(BaseModel):
    """Query parameters for an object's nearest neighbors."""

    model_config = ConfigDict(extra="forbid")

    topK: int = Field(default=10, ge=1, le=100, description="Neighbors to return.")
    brokerId: int | None = Field(
        default=None,
        description="Broker to search. Defaults to the first active broker "
        "that serves similarity search.",
    )


class NeighborClassification(BaseModel):
    """The most recent human classification of a neighbor."""

    model_config = ConfigDict(extra="forbid")

    classification: str
    probability: float | None = None
    taxonomy_id: int


class SimilarSourceResponse(BaseModel):
    """One neighbor of an object in the broker's embedding space."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    score: float = Field(description="Cosine similarity, higher is closer.")
    jd: float | None = Field(
        default=None, description="JD of the alert the embedding came from."
    )
    model_label: str | None = Field(
        default=None, description="The broker model's class for the neighbor."
    )
    model_probability: float | None = None
    in_skyportal: bool = Field(
        description="Whether the requester can read this object here."
    )
    redshift: float | None = None
    classification: NeighborClassification | None = None


class SimilarSourcesResponse(BaseModel):
    """An object's nearest neighbors, best first."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    broker_id: int
    neighbors: list[SimilarSourceResponse] = Field(default_factory=list)


class SimilarityVettingGetQuery(BaseModel):
    """Query parameters for the neighbor vetting queue."""

    model_config = ConfigDict(extra="forbid")

    days: float = Field(default=1, gt=0, le=30, description="Look back this many days.")
    topK: int = Field(default=50, ge=1, le=100, description="Neighbors per source.")
    minLabeled: int = Field(
        default=3, ge=1, description="Fewest human-classified neighbors to judge."
    )
    maxAgreement: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Keep sources whose share of agreeing neighbors is at most this.",
    )
    groupIds: list[int] | None = Field(
        default=None, description="Only sources saved to these groups."
    )
    brokerId: int | None = Field(default=None, description="Broker to search.")


class SimilarityVettingItem(BaseModel):
    """A source whose human-classified neighbors disagree with its class."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    classification: str
    probability: float | None = None
    classified_at: str
    labeled_neighbors: int
    agreement: float = Field(
        description="Share of labeled neighbors on the same taxonomy branch."
    )
    neighbor_classes: dict[str, int] = Field(default_factory=dict)


class SimilarityVettingResponse(BaseModel):
    """Recently classified sources whose neighbors disagree, worst first."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int
    checked: int = Field(description="Classified sources searched.")
    items: list[SimilarityVettingItem] = Field(default_factory=list)


__all__ = [
    "NeighborClassification",
    "SimilarSourceResponse",
    "SimilarSourcesGetQuery",
    "SimilarSourcesResponse",
    "SimilarityVettingGetQuery",
    "SimilarityVettingItem",
    "SimilarityVettingResponse",
]
