"""circular_created_at on gcn event extractions

Revision ID: d3f7a1b9c204
Revises: b4e9d17c3a80
Create Date: 2026-09-02

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d3f7a1b9c204"
down_revision = "b4e9d17c3a80"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "gcneventextractions",
        sa.Column("circular_created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_gcneventextractions_circular_created_at"),
        "gcneventextractions",
        ["circular_created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_gcneventextractions_circular_created_at"),
        table_name="gcneventextractions",
    )
    op.drop_column("gcneventextractions", "circular_created_at")
