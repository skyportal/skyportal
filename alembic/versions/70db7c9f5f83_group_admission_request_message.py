"""Add group admission request message

Revision ID: 70db7c9f5f83
Revises: a2f6c8d1e4b7
Create Date: 2026-10-13

"""

import sqlalchemy as sa

from alembic import op

revision = "70db7c9f5f83"
down_revision = "a2f6c8d1e4b7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "groupadmissionrequests", sa.Column("message", sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column("groupadmissionrequests", "message")
