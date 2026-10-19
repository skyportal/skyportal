"""feedback

Revision ID: e8e0a8efa6d2
Revises: d2e53492f191
Create Date: 2026-09-29

"""

import sqlalchemy as sa

from alembic import op

revision = "e8e0a8efa6d2"
down_revision = "d2e53492f191"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feedbacks",
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feedbacks_author_id"), "feedbacks", ["author_id"], unique=False
    )
    op.create_index(
        op.f("ix_feedbacks_created_at"), "feedbacks", ["created_at"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_feedbacks_created_at"), table_name="feedbacks")
    op.drop_index(op.f("ix_feedbacks_author_id"), table_name="feedbacks")
    op.drop_table("feedbacks")
