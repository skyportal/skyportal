"""Give a GcnEvent a summary

Mirrors objs.summary/summary_history: a narrative a human can edit and a
record of the ones written before it.

Revision ID: a3f7d21c8b45
Revises: b1e4a7c92f10
Create Date: 2026-09-04

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "a3f7d21c8b45"
down_revision = "b1e4a7c92f10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("gcnevents", sa.Column("summary", sa.String(), nullable=True))
    op.add_column(
        "gcnevents",
        sa.Column(
            "summary_history", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade():
    op.drop_column("gcnevents", "summary_history")
    op.drop_column("gcnevents", "summary")
