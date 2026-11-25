"""Schedule assistant queries.

Revision ID: 964a3d287b51
Revises: 510bb053e9e1
"""

import sqlalchemy as sa

from alembic import op

revision = "964a3d287b51"
down_revision = "510bb053e9e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("assistantmessages", sa.Column("run_status", sa.String()))
    op.add_column("assistantqueries", sa.Column("source_id", sa.String()))
    op.add_column("assistantqueries", sa.Column("interval_minutes", sa.Integer()))
    op.add_column("assistantqueries", sa.Column("next_run_at", sa.DateTime()))
    op.add_column("assistantqueries", sa.Column("last_run_at", sa.DateTime()))
    op.add_column("assistantqueries", sa.Column("last_run_count", sa.Integer()))
    op.create_index(
        "ix_assistantqueries_next_run_at", "assistantqueries", ["next_run_at"]
    )


def downgrade():
    op.drop_index("ix_assistantqueries_next_run_at", table_name="assistantqueries")
    for name in (
        "last_run_count",
        "last_run_at",
        "next_run_at",
        "interval_minutes",
        "source_id",
    ):
        op.drop_column("assistantqueries", name)
    op.drop_column("assistantmessages", "run_status")
