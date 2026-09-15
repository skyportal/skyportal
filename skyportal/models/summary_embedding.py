"""The vector for a source's summary, when the embeddings store is pgvector.

Registered on the metadata rather than mapped: nothing queries it as an object,
and the searches in `skyportal.utils.embedding_store` are Core statements so they
can compose with the access-controlled select for objs.
"""

__all__ = ["SummaryEmbedding", "Vector"]

import sqlalchemy as sa

from baselayer.app.models import Base


class Vector(sa.types.UserDefinedType):
    """pgvector's type, so the column can be created and cast to."""

    cache_ok = True

    def get_col_spec(self, **kw):
        return "vector"


SummaryEmbedding = sa.Table(
    "summary_embeddings",
    Base.metadata,
    sa.Column(
        "obj_id",
        sa.Text,
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # No declared width, so the embedding model can be changed without a
    # migration. Postgres will not compare vectors of different widths, so reads
    # are scoped to one model and vectors from an earlier one sit unread.
    sa.Column("embedding", Vector, nullable=False),
    sa.Column("model", sa.Text, nullable=False, index=True),
    sa.Column("summary", sa.Text),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
    sa.Column(
        "modified",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
)


@sa.event.listens_for(SummaryEmbedding, "before_create")
def _ensure_vector_extension(target, connection, **kw):
    """Make sure the `vector` type exists before the column that uses it.

    Installing an extension is a superuser act, and the application role is not
    one, so this only attempts it when the extension is genuinely absent -- an
    already-installed extension short-circuits before the privilege check. Where
    it is missing and cannot be added, say which command an administrator has to
    run rather than surfacing a bare permissions error from create_all.
    """
    if connection.scalar(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ):
        return
    try:
        connection.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception as e:
        raise RuntimeError(
            f"The {target.name} table needs pgvector's `vector` type, and this "
            "role may not install extensions. Ask an administrator to run, once, "
            f"in database {connection.engine.url.database}:\n"
            "    CREATE EXTENSION vector;"
        ) from e
