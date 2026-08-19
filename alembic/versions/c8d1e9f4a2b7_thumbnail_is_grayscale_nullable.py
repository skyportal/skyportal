"""thumbnail is_grayscale nullable

Revision ID: c8d1e9f4a2b7
Revises: 9bf2f46e850c
Create Date: 2026-07-14 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8d1e9f4a2b7"
down_revision = "9bf2f46e850c"
branch_labels = None
depends_on = None


def upgrade():
    # NULL now means "remote thumbnail not yet classified"; the thumbnail_queue
    # service fills it in off the request path.
    op.alter_column(
        "thumbnails", "is_grayscale", existing_type=sa.Boolean(), nullable=True
    )


def downgrade():
    op.execute("UPDATE thumbnails SET is_grayscale = false WHERE is_grayscale IS NULL")
    op.alter_column(
        "thumbnails", "is_grayscale", existing_type=sa.Boolean(), nullable=False
    )
