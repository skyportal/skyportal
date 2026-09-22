"""shared assistant queries and their subscriptions

Revision ID: d4e5f6a7b8c9
Revises: b7f3a2c1d4e5
Create Date: 2026-09-22 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "b7f3a2c1d4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assistantqueries",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column(
            "context_type",
            sa.String(),
            server_default=sa.text("'source'"),
            nullable=False,
        ),
        sa.Column("analysis_service_match", sa.String(), nullable=True),
        sa.Column("notify_groups", JSONB(), nullable=True),
        sa.Column(
            "active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "dry_run", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistantqueries_created_at"),
        "assistantqueries",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assistantqueries_owner_id"), "assistantqueries", ["owner_id"]
    )
    op.create_index(
        op.f("ix_assistantqueries_group_id"), "assistantqueries", ["group_id"]
    )
    op.create_index(
        op.f("ix_assistantqueries_analysis_service_match"),
        "assistantqueries",
        ["analysis_service_match"],
    )

    op.create_table(
        "assistantquerysubscriptions",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("query_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["query_id"], ["assistantqueries.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "query_id", "user_id", name="assistant_query_subscription_uniq"
        ),
    )
    op.create_index(
        op.f("ix_assistantquerysubscriptions_created_at"),
        "assistantquerysubscriptions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assistantquerysubscriptions_query_id"),
        "assistantquerysubscriptions",
        ["query_id"],
    )
    op.create_index(
        op.f("ix_assistantquerysubscriptions_user_id"),
        "assistantquerysubscriptions",
        ["user_id"],
    )


def downgrade():
    op.drop_table("assistantquerysubscriptions")
    op.drop_table("assistantqueries")
