"""Searching the summary embeddings kept in pgvector.

Reads are scoped to one embedding model, since Postgres cannot compare vectors of
different widths. Callers pass the objs the requester may read as a subquery, so
the access rule stays in `Source.select` rather than being copied here.
"""

__all__ = [
    "PGVECTOR",
    "store_location",
    "vector_literal",
    "upsert_embedding",
    "search_embeddings",
    "search_embeddings_by_obj",
]

import sqlalchemy as sa

from ..models.summary_embedding import SummaryEmbedding, Vector

PGVECTOR = "pgvector"

_embeddings = SummaryEmbedding.c
# Lightweight handles for the few columns a search reads off other tables.
_objs = sa.table("objs", sa.column("id"), sa.column("redshift"), sa.column("summary"))
_classifications = sa.table(
    "classifications", sa.column("obj_id"), sa.column("classification")
)


def store_location(config: dict) -> str | None:
    """The configured backend name, lowercased, or None when unset."""
    location = (config or {}).get("location")
    return str(location).strip().lower() if location else None


def vector_literal(vector) -> str:
    """A float sequence in the text form pgvector parses, cast in the statement."""
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


async def upsert_embedding(session, obj_id, vector, model):
    """Record one summary's vector, replacing any the obj already had."""
    await session.execute(
        sa.text(
            "INSERT INTO summary_embeddings (obj_id, embedding, model) "
            "VALUES (:obj_id, CAST(:embedding AS vector), :model) "
            "ON CONFLICT (obj_id) DO UPDATE SET "
            "embedding = EXCLUDED.embedding, model = EXCLUDED.model, "
            "modified = now()"
        ),
        {
            "obj_id": obj_id,
            "embedding": vector_literal(vector),
            "model": model,
        },
    )


def _restrict(stmt, model, accessible_objs, z_min, z_max, classification_types):
    """Everything a search is allowed to look at, before similarity is considered."""
    stmt = stmt.where(_embeddings.model == model)

    if accessible_objs is not None:
        stmt = stmt.where(_embeddings.obj_id.in_(accessible_objs))

    # Read against the live tables rather than a copy taken when the summary was
    # written, so a reclassification is reflected without re-embedding.
    if z_min is not None or z_max is not None:
        stmt = stmt.where(
            sa.exists(
                sa.select(sa.literal(1))
                .select_from(_objs)
                .where(
                    _objs.c.id == _embeddings.obj_id,
                    # A source with no redshift cannot satisfy a redshift cut.
                    _objs.c.redshift.isnot(None),
                    *([_objs.c.redshift >= z_min] if z_min is not None else []),
                    *([_objs.c.redshift <= z_max] if z_max is not None else []),
                )
            )
        )

    if classification_types:
        stmt = stmt.where(
            sa.exists(
                sa.select(sa.literal(1))
                .select_from(_classifications)
                .where(
                    _classifications.c.obj_id == _embeddings.obj_id,
                    _classifications.c.classification.in_(list(classification_types)),
                )
            )
        )
    return stmt


async def _nearest(session, target, k, model, accessible_objs, z_min, z_max, classes):
    """The k rows closest to `target`, scored 1 (identical) to 0 (unrelated)."""
    distance = _embeddings.embedding.op("<=>", return_type=sa.Float)(target)
    stmt = sa.select(
        _embeddings.obj_id,
        (1 - distance).label("score"),
        # From the obj, so an edited summary is not left behind by a copy.
        sa.select(_objs.c.summary)
        .where(_objs.c.id == _embeddings.obj_id)
        .scalar_subquery()
        .label("summary"),
        sa.select(_objs.c.redshift)
        .where(_objs.c.id == _embeddings.obj_id)
        .scalar_subquery()
        .label("redshift"),
        sa.select(sa.func.array_agg(sa.distinct(_classifications.c.classification)))
        .where(_classifications.c.obj_id == _embeddings.obj_id)
        .scalar_subquery()
        .label("classes"),
    )
    stmt = _restrict(stmt, model, accessible_objs, z_min, z_max, classes)
    stmt = stmt.order_by(distance).limit(k)

    rows = (await session.execute(stmt)).mappings().all()
    return [
        {
            "id": row["obj_id"],
            "score": float(row["score"]),
            "metadata": {
                "summary": row["summary"],
                "redshift": row["redshift"],
                "class": row["classes"],
            },
        }
        for row in rows
    ]


async def search_embeddings(
    session,
    vector,
    k,
    model,
    accessible_objs=None,
    z_min=None,
    z_max=None,
    classification_types=None,
):
    """Summaries most similar to `vector`, nearest first."""
    target = sa.cast(sa.literal(vector_literal(vector)), Vector())
    return await _nearest(
        session, target, k, model, accessible_objs, z_min, z_max, classification_types
    )


async def search_embeddings_by_obj(
    session,
    obj_id,
    k,
    model,
    accessible_objs=None,
    z_min=None,
    z_max=None,
    classification_types=None,
):
    """Summaries most similar to `obj_id`'s own, which is itself excluded."""
    anchor_where = [_embeddings.obj_id == obj_id, _embeddings.model == model]
    if accessible_objs is not None:
        anchor_where.append(_embeddings.obj_id.in_(accessible_objs))
    anchor = await session.scalar(sa.select(_embeddings.embedding).where(*anchor_where))
    if anchor is None:
        return []

    target = sa.cast(sa.literal(anchor), Vector())
    results = await _nearest(
        session,
        target,
        k + 1,
        model,
        accessible_objs,
        z_min,
        z_max,
        classification_types,
    )
    return [r for r in results if r["id"] != obj_id][:k]
