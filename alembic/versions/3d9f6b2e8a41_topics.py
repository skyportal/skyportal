"""topics

Revision ID: 3d9f6b2e8a41
Revises: fc2e1adbcf93
Create Date: 2026-11-02

"""

import sqlalchemy as sa

from alembic import op

revision = "3d9f6b2e8a41"
down_revision = "fc2e1adbcf93"
branch_labels = None
depends_on = None

INDEXES = {
    "topics": ("created_at", "creator_id"),
    "topic_subscriptions": ("created_at", "topic_id", "user_id"),
    "topic_sources": ("author_id", "created_at", "obj_id", "topic_id"),
}


def upgrade():
    op.create_table(
        "topics",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column(
            "classifications",
            sa.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "tag_ids", sa.ARRAY(sa.Integer()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "topic_subscriptions",
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_id", "user_id", name="topic_subscription_uniq"),
    )
    op.create_table(
        "topic_sources",
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("obj_id", sa.String(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["obj_id"], ["objs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_id", "obj_id", name="topic_source_uniq"),
    )
    for table, columns in INDEXES.items():
        for column in columns:
            op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def downgrade():
    for table, columns in reversed(INDEXES.items()):
        for column in columns:
            op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
    op.drop_table("topic_sources")
    op.drop_table("topic_subscriptions")
    op.drop_table("topics")
