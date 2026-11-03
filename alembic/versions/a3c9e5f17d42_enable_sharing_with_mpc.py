"""Let a sharing service submit moving-object tracks to the MPC

Revision ID: a3c9e5f17d42
Revises: 3d9f6b2e8a41
Create Date: 2026-11-04 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "a3c9e5f17d42"
down_revision = "3d9f6b2e8a41"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sharingservices",
        sa.Column(
            "enable_sharing_with_mpc",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade():
    op.drop_column("sharingservices", "enable_sharing_with_mpc")
