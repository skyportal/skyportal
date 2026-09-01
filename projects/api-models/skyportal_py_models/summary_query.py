"""Response models for ``/api/summary_query``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SummaryQueryMatchResponse(BaseModel):
    """One vector-store hit for a summary query (not a SkyPortal model).

    The shape is defined by the Pinecone client: when ``q`` is used the
    handler rebuilds each hit as exactly ``id``, ``score`` and ``metadata``,
    but when ``objID`` is used it passes the raw ``matches`` of the Pinecone
    query response straight through, so the remaining fields are Pinecone's
    ``ScoredVector`` attributes (``values``, ``sparse_values``, serialized as
    ``sparseValues``). ``metadata`` holds whatever was indexed alongside the
    summary (``redshift``, ``class``, ...), so it stays free-form.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    id: str
    score: float | None = None
    values: list[float] | None = None
    sparse_values: dict[str, Any] | None = Field(alias="sparseValues", default=None)
    metadata: dict[str, Any] | None = None


class SummaryQueryResultsResponse(BaseModel):
    """Results of a source summary similarity search."""

    model_config = ConfigDict(extra="forbid")

    query_results: list[SummaryQueryMatchResponse] = Field(default_factory=list)


class SummaryQueryPost(BaseModel):
    """Payload for a source summary similarity search."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    q: str | None = None
    obj_id: str | None = Field(alias="objID", default=None)
    k: int | None = None
    z_min: float | None = None
    z_max: float | None = None
    classification_types: list[str] | None = Field(
        alias="classificationTypes", default=None
    )
