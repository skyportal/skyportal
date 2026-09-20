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
    """Install pgvector's `vector` type, unless it is there or we may not.

    Installing an extension is a superuser act, so an existing one must
    short-circuit before the privilege check.
    """
    if connection.scalar(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ):
        return
    try:
        connection.execute(sa.text("CREATE EXTENSION vector"))
    except Exception as e:
        # SQLSTATE 0A000: absent from the server, not a privilege problem.
        if getattr(getattr(e, "orig", None), "sqlstate", None) == "0A000":
            fix = (
                "which is not installed on this PostgreSQL server. Install it "
                "(`brew install pgvector`, `apt install postgresql-17-pgvector`, "
                "...), then run, once,"
            )
        else:
            fix = (
                "and this role may not install extensions. Ask an administrator "
                "to run, once,"
            )
        raise RuntimeError(
            f"The summary_embeddings table needs pgvector's `vector` type, {fix} "
            f"in database {connection.engine.url.database}:\n"
            "    CREATE EXTENSION vector;"
        ) from e


@sa.event.listens_for(SummaryEmbedding, "before_create")
def _create_vector_extension(target, connection, **kw):
    """Make sure the `vector` type exists before the column that uses it."""
    ensure_vector_extension(connection)
