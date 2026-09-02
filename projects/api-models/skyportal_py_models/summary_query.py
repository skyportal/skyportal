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


class SummaryQueryPostBody(BaseModel):
    """Request body for a summary similarity search."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(
        default=None,
        description='The query string. E.g. "What sources are associated with '
        'an NGC galaxy?"',
    )
    objID: str | None = Field(
        default=None,
        description="The objID of the source which has a summary to be used as "
        "the query. That is, return the list of sources most similar to the "
        "summary of this source. Ignored if q is provided.",
    )
    k: int = Field(default=5, description="Max number of sources to return. Default 5.")
    z_min: float | None = Field(
        default=None,
        description="Minimum redshift to consider of queries sources. If None or "
        "missing, then no lower limit is applied.",
    )
    z_max: float | None = Field(
        default=None,
        description="Maximum redshift to consider of queries sources. If None or "
        "missing, then no upper limit is applied.",
    )
    classificationTypes: list[str] | None = Field(
        default=None,
        description="List of classification types to consider. If [] or missing, "
        "then all classification types are considered.",
    )


class SummaryQueryPostResponse(BaseModel):
    """Sources whose summaries match the query."""

    query_results: list[dict[str, Any]] = Field(
        description="Matching sources, most similar first, with their scores"
    )
