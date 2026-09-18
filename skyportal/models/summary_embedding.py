"""The vector for a source's summary, when the embeddings store is pgvector."""

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
    # No declared width, so the embedding model can change without a migration.
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
    """Install pgvector's `vector` type, unless it is there or we cannot.

    Installing an extension is a superuser act, so an existing one must
    short-circuit before the privilege check. A server without pgvector at
    all fails for a different reason than one that will not let this role
    install it, and wants a different fix, so they are told apart here.
    """
    if connection.scalar(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ):
        return
    database = connection.engine.url.database
    if not connection.scalar(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    ):
        raise RuntimeError(
            "The summary_embeddings table needs pgvector's `vector` type, "
            "which this PostgreSQL server does not carry. Install pgvector "
            "alongside the server -- under Docker, run the pgvector/pgvector "
            "image in place of postgres -- and then, in database "
            f"{database}:\n"
            "    CREATE EXTENSION vector;"
        )
    try:
        connection.execute(sa.text("CREATE EXTENSION vector"))
    except Exception as e:
        raise RuntimeError(
            "The summary_embeddings table needs pgvector's `vector` type, and "
            "this role may not install extensions. Ask an administrator to run, "
            f"once, in database {database}:\n"
            "    CREATE EXTENSION vector;"
        ) from e


@sa.event.listens_for(SummaryEmbedding, "before_create")
def _create_vector_extension(target, connection, **kw):
    """Make sure the `vector` type exists before the column that uses it."""
    ensure_vector_extension(connection)
