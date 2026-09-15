"""summary embeddings

Revision ID: b7e4c1a90f33
Revises: c4d81f2a6b03
Create Date: 2026-09-14 18:40:00.000000

"""

from alembic import op
from skyportal.utils.embedding_store import ensure_vector_extension

# revision identifiers, used by alembic.
revision = "b7e4c1a90f33"
down_revision = "c4d81f2a6b03"
branch_labels = None
depends_on = None

# Raw DDL: `vector` is pgvector's own type, and spelling it here avoids
# registering it with SQLAlchemy for one table.
#
# The column declares no width, so the embedding model can change without a
# migration. Postgres will not compare vectors of different widths, so reads are
# scoped to the model named in the config and vectors from an earlier model sit
# unread until they are written over.
#
# No ANN index: an exact scan over a few thousand summaries is immediate, and
# HNSW would pin the width that the missing declaration deliberately leaves open.
CREATE = """
CREATE TABLE summary_embeddings (
    obj_id text PRIMARY KEY REFERENCES objs (id) ON DELETE CASCADE,
    embedding vector NOT NULL,
    model text NOT NULL,
    summary text,
    created_at timestamptz NOT NULL DEFAULT now(),
    modified timestamptz NOT NULL DEFAULT now()
)
"""


def upgrade():
    ensure_vector_extension(op.get_bind())
    op.execute(CREATE)
    op.execute("CREATE INDEX ix_summary_embeddings_model ON summary_embeddings (model)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS summary_embeddings")
