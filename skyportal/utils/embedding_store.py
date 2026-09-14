"""Where source-summary embeddings are kept, and how they are searched.

The backend is named by `embeddings_store.summary.location`: `pinecone` talks to
the hosted service, `pgvector` keeps the vectors in SkyPortal's own database.

pgvector holds them in a column with no declared width, so changing embedding
model needs no migration. Postgres will not compare vectors of different widths,
though, so every read is scoped to the model named in the config: vectors from a
previous model stay in place, ignored, until they are written over.
"""

__all__ = [
    "PGVECTOR",
    "PINECONE",
    "store_location",
    "vector_literal",
    "upsert_embedding",
    "search_embeddings",
    "search_embeddings_by_obj",
]

from typing import Any

import sqlalchemy as sa

PINECONE = "pinecone"
PGVECTOR = "pgvector"


def store_location(config: dict) -> str | None:
    """The configured backend name, lowercased, or None when unset."""
    location = (config or {}).get("location")
    return str(location).strip().lower() if location else None


def vector_literal(vector) -> str:
    """A float sequence in the text form pgvector parses, for binding as a param.

    Sent as text and cast in the statement, which keeps the driver free of any
    pgvector-specific type registration.
    """
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


def _filtered_obj_ids(z_min, z_max, classification_types):
    """A subquery of obj ids passing the redshift and classification filters.

    Read against the live tables rather than a copy taken when the summary was
    written, so a reclassification is reflected without re-embedding.
    """
    clauses = []
    if z_min is not None:
        clauses.append("o.redshift >= :z_min")
    if z_max is not None:
        clauses.append("o.redshift <= :z_max")
    if z_min is not None or z_max is not None:
        # A source with no redshift cannot satisfy a redshift cut.
        clauses.append("o.redshift IS NOT NULL")
    if classification_types:
        clauses.append(
            "EXISTS (SELECT 1 FROM classifications c "
            "WHERE c.obj_id = o.id AND c.classification = ANY(:classes))"
        )
    return " AND ".join(clauses)


async def upsert_embedding(session, obj_id, vector, model, summary=None):
    """Record one summary's vector, replacing any the obj already had."""
    await session.execute(
        sa.text(
            "INSERT INTO summary_embeddings (obj_id, embedding, model, summary) "
            "VALUES (:obj_id, CAST(:embedding AS vector), :model, :summary) "
            "ON CONFLICT (obj_id) DO UPDATE SET "
            "embedding = EXCLUDED.embedding, model = EXCLUDED.model, "
            "summary = EXCLUDED.summary, modified = now()"
        ),
        {
            "obj_id": obj_id,
            "embedding": vector_literal(vector),
            "model": model,
            "summary": summary,
        },
    )


def _search_statement(model, k, z_min, z_max, classification_types, by_obj=False):
    """The similarity query and its parameters.

    `<=>` is cosine distance, so 0 is identical and 2 is opposite; the score
    returned is 1 - distance, matching pinecone's cosine similarity.
    """
    params: dict[str, Any] = {"model": model, "k": k}
    where = ["e.model = :model"]
    if by_obj:
        # The obj itself would otherwise always come back as its own best match.
        where.append("e.obj_id != :obj_id")
    filters = _filtered_obj_ids(z_min, z_max, classification_types)
    join = ""
    if filters:
        join = "JOIN objs o ON o.id = e.obj_id"
        where.append(filters)
        if z_min is not None:
            params["z_min"] = z_min
        if z_max is not None:
            params["z_max"] = z_max
        if classification_types:
            params["classes"] = list(classification_types)

    if by_obj:
        target = (
            "(SELECT embedding FROM summary_embeddings "
            "WHERE obj_id = :obj_id AND model = :model)"
        )
    else:
        target = "CAST(:embedding AS vector)"

    sql = (
        f"SELECT e.obj_id, e.summary, 1 - (e.embedding <=> {target}) AS score "
        f"FROM summary_embeddings e {join} "
        f"WHERE {' AND '.join(where)} "
        f"ORDER BY e.embedding <=> {target} LIMIT :k"
    )
    return sql, params


async def _run_search(session, sql, params):
    rows = (await session.execute(sa.text(sql), params)).mappings().all()
    return [
        {
            "id": row["obj_id"],
            "score": float(row["score"]),
            "metadata": {"summary": row["summary"]},
        }
        for row in rows
    ]


async def search_embeddings(
    session, vector, k, model, z_min=None, z_max=None, classification_types=None
):
    """Summaries most similar to `vector`, nearest first."""
    sql, params = _search_statement(model, k, z_min, z_max, classification_types)
    params["embedding"] = vector_literal(vector)
    return await _run_search(session, sql, params)


async def search_embeddings_by_obj(
    session, obj_id, k, model, z_min=None, z_max=None, classification_types=None
):
    """Summaries most similar to `obj_id`'s own, which is itself excluded."""
    sql, params = _search_statement(
        model, k, z_min, z_max, classification_types, by_obj=True
    )
    params["obj_id"] = obj_id
    return await _run_search(session, sql, params)
