"""Record who created an instrument

Adds instruments.created_by_id so the creator can edit or delete an instrument
without Manage instruments. Existing instruments have no creator.

Revision ID: d9d858453a23
Revises: f2a6c81d57b3
Create Date: 2026-10-29 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "d9d858453a23"
down_revision = "f2a6c81d57b3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "instruments",
        sa.Column("created_by_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_instruments_created_by_id"),
        "instruments",
        ["created_by_id"],
        unique=False,
    )
    op.create_foreign_key(
        "instruments_created_by_id_fkey",
        "instruments",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "instruments_created_by_id_fkey", "instruments", type_="foreignkey"
    )
    op.drop_index(op.f("ix_instruments_created_by_id"), table_name="instruments")
    op.drop_column("instruments", "created_by_id")
