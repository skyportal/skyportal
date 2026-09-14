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

# The type has to exist before the column using it can be created, and a fresh
# database is built from this metadata rather than from the migrations.
sa.event.listen(
    SummaryEmbedding,
    "before_create",
    sa.DDL("CREATE EXTENSION IF NOT EXISTS vector"),
)
