"""feedback assignee

Revision ID: a2f6c8d1e4b7
Revises: 28442e0a1830
Create Date: 2026-10-13

"""

import sqlalchemy as sa

from alembic import op

revision = "a2f6c8d1e4b7"
down_revision = "28442e0a1830"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("feedbacks", sa.Column("assignee_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_feedbacks_assignee_id"), "feedbacks", ["assignee_id"], unique=False
    )
    op.create_foreign_key(
        "feedbacks_assignee_id_fkey",
        "feedbacks",
        "users",
        ["assignee_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("feedbacks_assignee_id_fkey", "feedbacks", type_="foreignkey")
    op.drop_index(op.f("ix_feedbacks_assignee_id"), table_name="feedbacks")
    op.drop_column("feedbacks", "assignee_id")
