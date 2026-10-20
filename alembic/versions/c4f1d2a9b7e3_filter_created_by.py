"""filter created_by

Revision ID: c4f1d2a9b7e3
Revises: dbb949db3e2c
Create Date: 2026-10-20

"""

import sqlalchemy as sa

from alembic import op

revision = "c4f1d2a9b7e3"
down_revision = "dbb949db3e2c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("filters", sa.Column("created_by_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_filters_created_by_id"), "filters", ["created_by_id"], unique=False
    )
    op.create_foreign_key(
        "filters_created_by_id_fkey",
        "filters",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("filters_created_by_id_fkey", "filters", type_="foreignkey")
    op.drop_index(op.f("ix_filters_created_by_id"), table_name="filters")
    op.drop_column("filters", "created_by_id")
