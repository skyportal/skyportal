"""summary embeddings

Revision ID: b7e4c1a90f33
Revises: c4d81f2a6b03
Create Date: 2026-09-14 18:40:00.000000

"""

from alembic import op
from skyportal.models.summary_embedding import ensure_vector_extension

# revision identifiers, used by alembic.
revision = "b7e4c1a90f33"
down_revision = "c4d81f2a6b03"
branch_labels = None
depends_on = None

# No declared width, and so no ANN index: either would pin the embedding model.
CREATE = """
CREATE TABLE summary_embeddings (
    obj_id text PRIMARY KEY REFERENCES objs (id) ON DELETE CASCADE,
    embedding vector NOT NULL,
    model text NOT NULL,
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
