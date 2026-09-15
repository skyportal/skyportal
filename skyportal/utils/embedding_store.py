"""Searching the summary embeddings kept in pgvector.

Reads are scoped to one embedding model, since Postgres cannot compare vectors of
different widths. Callers pass the objs the requester may read as a subquery, so
the access rule stays in `Source.select` rather than being copied here.
"""

__all__ = [
    "vector_literal",
    "upsert_embedding",
    "search_embeddings",
    "search_embeddings_by_obj",
]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from ..models import Obj, SummaryEmbedding
from ..models.summary_embedding import Vector

_embeddings = SummaryEmbedding.c
_objs = Obj.__table__


def vector_literal(vector) -> str:
    """A float sequence in the text form pgvector parses, cast in the statement."""
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


def upsert_embedding(obj_id, vector, model):
    """The statement recording one summary's vector, replacing any the obj had."""
    stmt = insert(SummaryEmbedding).values(
        obj_id=obj_id,
        embedding=sa.cast(vector_literal(vector), Vector()),
        model=model,
    )
    return stmt.on_conflict_do_update(
        index_elements=[_embeddings.obj_id],
        set_={
            "embedding": stmt.excluded.embedding,
            "model": stmt.excluded.model,
            "modified": sa.func.now(),
        },
    )


def _restrict(
    stmt, model, accessible_objs, classifications, z_min, z_max, classification_types
):
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
                .select_from(classifications)
                .where(
                    classifications.c.obj_id == _embeddings.obj_id,
                    classifications.c.classification.in_(list(classification_types)),
                )
            )
        )
    return stmt


async def _nearest(
    session, target, k, model, accessible_objs, classifications, z_min, z_max, classes
):
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
        sa.select(sa.func.array_agg(sa.distinct(classifications.c.classification)))
        .where(classifications.c.obj_id == _embeddings.obj_id)
        .scalar_subquery()
        .label("classes"),
    )
    stmt = _restrict(
        stmt, model, accessible_objs, classifications, z_min, z_max, classes
    )
    # Nothing is near a target that does not exist: an obj with no stored vector
    # gives a NULL target, and every distance to it is NULL.
    stmt = stmt.where(distance.isnot(None)).order_by(distance).limit(k)

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
    accessible_objs,
    accessible_classifications,
    z_min=None,
    z_max=None,
    classification_types=None,
):
    """Summaries most similar to `vector`, nearest first."""
    target = sa.cast(sa.literal(vector_literal(vector)), Vector())
    return await _nearest(
        session,
        target,
        k,
        model,
        accessible_objs,
        accessible_classifications.subquery(),
        z_min,
        z_max,
        classification_types,
    )


async def search_embeddings_by_obj(
    session,
    obj_id,
    k,
    model,
    accessible_objs,
    accessible_classifications,
    z_min=None,
    z_max=None,
    classification_types=None,
):
    """Summaries most similar to `obj_id`'s own, which is itself excluded."""
    anchor = SummaryEmbedding.alias("anchor")
    anchor_where = [anchor.c.obj_id == obj_id, anchor.c.model == model]
    if accessible_objs is not None:
        anchor_where.append(anchor.c.obj_id.in_(accessible_objs))
    # Read in place rather than fetched and sent back as a literal.
    target = sa.select(anchor.c.embedding).where(*anchor_where).scalar_subquery()
    results = await _nearest(
        session,
        target,
        k + 1,
        model,
        accessible_objs,
        accessible_classifications.subquery(),
        z_min,
        z_max,
        classification_types,
    )
    return [r for r in results if r["id"] != obj_id][:k]
