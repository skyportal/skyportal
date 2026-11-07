"""Link the public version of a source comment to its private version

Revision ID: e5b1d7c3a920
Revises: c4e8b2a6d913
Create Date: 2026-11-07 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "e5b1d7c3a920"
down_revision = "c4e8b2a6d913"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "comments",
        sa.Column("private_version_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_comments_private_version_id"),
        "comments",
        ["private_version_id"],
        unique=False,
    )
    op.create_foreign_key(
        "comments_private_version_id_fkey",
        "comments",
        "comments",
        ["private_version_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint(
        "comments_private_version_id_fkey", "comments", type_="foreignkey"
    )
    op.drop_index(op.f("ix_comments_private_version_id"), table_name="comments")
    op.drop_column("comments", "private_version_id")
