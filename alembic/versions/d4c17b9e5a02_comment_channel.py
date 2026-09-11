"""Add a channel to comments

Revision ID: d4c17b9e5a02
Revises: b3f2a7c14d58
Create Date: 2026-08-06 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4c17b9e5a02"
down_revision = "b3f2a7c14d58"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("comments", sa.Column("channel", sa.String(), nullable=True))
    op.create_index(op.f("ix_comments_channel"), "comments", ["channel"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_comments_channel"), table_name="comments")
    op.drop_column("comments", "channel")
