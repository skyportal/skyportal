"""assistant answer model and usage

Revision ID: c4f1e8a2b937
Revises: b3d8f2e61c47
Create Date: 2026-11-21

"""

import sqlalchemy as sa

from alembic import op

revision = "c4f1e8a2b937"
down_revision = "b3d8f2e61c47"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("assistantmessages", sa.Column("model", sa.String(), nullable=True))
    op.create_table(
        "assistantusages",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistantusages_created_at"),
        "assistantusages",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_assistantusages_created_at"), table_name="assistantusages")
    op.drop_table("assistantusages")
    op.drop_column("assistantmessages", "model")
