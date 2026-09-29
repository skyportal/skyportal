"""deployments

Revision ID: d2e53492f191
Revises: b8f3d21c07ae
Create Date: 2026-09-29

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "d2e53492f191"
down_revision = "b8f3d21c07ae"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deployments",
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("commit", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_deployments_created_at"),
        "deployments",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_deployments_created_at"), table_name="deployments")
    op.drop_table("deployments")
