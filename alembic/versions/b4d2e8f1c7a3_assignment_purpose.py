"""Assignment purpose

Revision ID: b4d2e8f1c7a3
Revises: e7a41c9d2b58
Create Date: 2026-11-12 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "b4d2e8f1c7a3"
down_revision = "e7a41c9d2b58"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "classicalassignments", sa.Column("purpose", sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column("classicalassignments", "purpose")
