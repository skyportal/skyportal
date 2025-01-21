"""remove Comment.attachment_type

Revision ID: d67d42b06b11
Revises: b559ca7ed34c
Create Date: 2020-11-05 22:14:34.521986

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d67d42b06b11"
down_revision = "b559ca7ed34c"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("comments", "attachment_type")


def downgrade():
    op.add_column(
        "comments",
        sa.Column("attachment_type", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
