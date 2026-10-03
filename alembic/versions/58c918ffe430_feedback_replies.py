"""feedback replies

Revision ID: 58c918ffe430
Revises: e8e0a8efa6d2
Create Date: 2026-09-30

"""

import sqlalchemy as sa

from alembic import op

revision = "58c918ffe430"
down_revision = "e8e0a8efa6d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feedback_replies",
        sa.Column("feedback_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feedback_id"], ["feedbacks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("author_id", "created_at", "feedback_id"):
        op.create_index(
            op.f(f"ix_feedback_replies_{column}"),
            "feedback_replies",
            [column],
            unique=False,
        )


def downgrade():
    for column in ("author_id", "created_at", "feedback_id"):
        op.drop_index(
            op.f(f"ix_feedback_replies_{column}"), table_name="feedback_replies"
        )
    op.drop_table("feedback_replies")
