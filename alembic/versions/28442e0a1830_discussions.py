"""discussions

Revision ID: 28442e0a1830
Revises: b7e1c4a9d320
Create Date: 2026-10-09

"""

import sqlalchemy as sa

from alembic import op

revision = "28442e0a1830"
down_revision = "b7e1c4a9d320"
branch_labels = None
depends_on = None

INDEXES = {
    "discussions": ("created_at", "creator_id", "group_id"),
    "discussion_members": ("created_at", "discussion_id", "user_id"),
    "discussion_messages": ("author_id", "created_at", "discussion_id"),
}


def upgrade():
    op.create_table(
        "discussions",
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("is_direct", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "discussion_members",
        sa.Column("discussion_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(), nullable=True),
        sa.Column("muted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["discussion_id"], ["discussions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discussion_id", "user_id", name="discussion_member_uniq"),
    )
    op.create_table(
        "discussion_messages",
        sa.Column("discussion_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["discussion_id"], ["discussions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for table, columns in INDEXES.items():
        for column in columns:
            op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def downgrade():
    for table, columns in reversed(INDEXES.items()):
        for column in columns:
            op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
    op.drop_table("discussion_messages")
    op.drop_table("discussion_members")
    op.drop_table("discussions")
