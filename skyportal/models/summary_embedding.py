"""The vector for a source's summary, when the embeddings store is pgvector.

Registered on the metadata rather than mapped: nothing queries it as an object,
and the searches in `skyportal.utils.embedding_store` are Core statements so they
can compose with the access-controlled select for objs.
"""

__all__ = ["SummaryEmbedding", "Vector", "ensure_vector_extension"]

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


@sa.event.listens_for(SummaryEmbedding, "before_create")
def _create_vector_extension(target, connection, **kw):
    """Make sure the `vector` type exists before the column that uses it."""
    ensure_vector_extension(connection)
