"""Conversations with the assistant

Revision ID: e5c1a83f7d92
Revises: b1e4a7c92f10
Create Date: 2026-09-05

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5c1a83f7d92"
down_revision = "b1e4a7c92f10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assistantmessages",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(), nullable=True),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column(
            "system", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("context_type", sa.String(), nullable=True),
        sa.Column("context_id", sa.String(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistantmessages_created_at"),
        "assistantmessages",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assistantmessages_user_id"),
        "assistantmessages",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assistantmessages_channel"),
        "assistantmessages",
        ["channel"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_assistantmessages_channel"), table_name="assistantmessages")
    op.drop_index(op.f("ix_assistantmessages_user_id"), table_name="assistantmessages")
    op.drop_index(
        op.f("ix_assistantmessages_created_at"), table_name="assistantmessages"
    )
    op.drop_table("assistantmessages")
