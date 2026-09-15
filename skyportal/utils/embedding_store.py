"""Where source-summary embeddings are kept, and how they are searched.

`embeddings_store.summary.location` names the store; `pgvector` keeps the vectors
in SkyPortal's own database, beside the summaries they were made from.

pgvector holds them in a column with no declared width, so changing embedding
model needs no migration. Postgres will not compare vectors of different widths,
though, so every read is scoped to the model named in the config: vectors from a
previous model stay in place, ignored, until they are written over.

Callers pass the objs the requester may read as a subquery. Keeping it out of
here means the one access rule in `Obj.select` decides, rather than a copy of it.
"""

__all__ = [
    "PGVECTOR",
    "ensure_vector_extension",
    "store_location",
    "vector_literal",
    "upsert_embedding",
    "search_embeddings",
    "search_embeddings_by_obj",
]

import sqlalchemy as sa

PGVECTOR = "pgvector"


class Vector(sa.types.UserDefinedType):
    """pgvector's type, named so a query can cast to it."""

    cache_ok = True

    def get_col_spec(self, **kw):
        return "vector"


# Lightweight table handles: the columns a search touches, not a second
# declaration of tables the ORM already maps.
_embeddings = sa.table(
    "summary_embeddings",
    sa.column("obj_id"),
    sa.column("embedding"),
    sa.column("model"),
    sa.column("summary"),
)
_objs = sa.table("objs", sa.column("id"), sa.column("redshift"))
_classifications = sa.table(
    "classifications", sa.column("obj_id"), sa.column("classification")
)


def ensure_vector_extension(connection):
    """Install pgvector's `vector` type, unless it is there or we may not.

    Installing an extension is a superuser act, so an already-installed one has
    to short-circuit before the privilege check, and a role that cannot install
    it gets told what an administrator has to run instead of a bare error.
    """
    if connection.scalar(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ):
        return
    try:
        connection.execute(sa.text("CREATE EXTENSION vector"))
    except Exception as e:
        raise RuntimeError(
            "The summary_embeddings table needs pgvector's `vector` type, and "
            "this role may not install extensions. Ask an administrator to run, "
            f"once, in database {connection.engine.url.database}:\n"
            "    CREATE EXTENSION vector;"
        ) from e


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


def _restrict(stmt, model, accessible_objs, z_min, z_max, classification_types):
    """Everything a search is allowed to look at, before similarity is considered."""
    stmt = stmt.where(_embeddings.c.model == model)

    if accessible_objs is not None:
        stmt = stmt.where(_embeddings.c.obj_id.in_(accessible_objs))

    # Read against the live tables rather than a copy taken when the summary was
    # written, so a reclassification is reflected without re-embedding.
    if z_min is not None or z_max is not None:
        stmt = stmt.where(
            sa.exists(
                sa.select(sa.literal(1))
                .select_from(_objs)
                .where(
                    _objs.c.id == _embeddings.c.obj_id,
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
                    _classifications.c.obj_id == _embeddings.c.obj_id,
                    _classifications.c.classification.in_(list(classification_types)),
                )
            )
        )
    return stmt


async def _nearest(session, target, k, model, accessible_objs, z_min, z_max, classes):
    """The k rows closest to `target`.

    `<=>` is cosine distance, so 0 is identical and 2 is opposite; the score
    returned is 1 - distance, so 1 is identical and 0 is unrelated.
    """
    distance = _embeddings.c.embedding.op("<=>")(target)
    stmt = sa.select(
        _embeddings.c.obj_id,
        _embeddings.c.summary,
        (1 - distance).label("score"),
    )
    stmt = _restrict(stmt, model, accessible_objs, z_min, z_max, classes)
    stmt = stmt.order_by(distance).limit(k)

    rows = (await session.execute(stmt)).mappings().all()
    return [
        {
            "id": row["obj_id"],
            "score": float(row["score"]),
            "metadata": {"summary": row["summary"]},
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
    """Summaries most similar to `obj_id`'s own, which is itself excluded.

    Nothing is returned for a source the requester cannot read: otherwise the
    neighbours of a private summary would be an answer about it.
    """
    anchor_where = [_embeddings.c.obj_id == obj_id, _embeddings.c.model == model]
    if accessible_objs is not None:
        anchor_where.append(_embeddings.c.obj_id.in_(accessible_objs))
    anchor = await session.scalar(
        sa.select(_embeddings.c.embedding).where(*anchor_where)
    )
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
