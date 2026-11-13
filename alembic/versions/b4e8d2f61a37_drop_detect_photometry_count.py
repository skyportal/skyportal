"""Drop objs.detect_photometry_count

Revision ID: b4e8d2f61a37
Revises: e7a41c9d2b58
Create Date: 2026-11-12 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "b4e8d2f61a37"
down_revision = "e7a41c9d2b58"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("objs", "detect_photometry_count")


def downgrade():
    op.add_column(
        "objs",
        sa.Column("detect_photometry_count", sa.Integer(), nullable=True),
    )
