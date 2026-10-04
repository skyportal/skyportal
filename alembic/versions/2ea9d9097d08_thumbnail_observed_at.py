"""thumbnail observed_at

Revision ID: 2ea9d9097d08
Revises: e5b2f7c19d04
Create Date: 2026-10-03

Adds the time of the alert observation a survey cutout comes from. Existing rows
stay NULL until a new alert rewrites their cutouts.
"""

import sqlalchemy as sa

from alembic import op

revision = "2ea9d9097d08"
down_revision = "e5b2f7c19d04"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("thumbnails", sa.Column("observed_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("thumbnails", "observed_at")
