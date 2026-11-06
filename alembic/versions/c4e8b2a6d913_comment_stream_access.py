"""Restrict a source comment by stream access

Revision ID: c4e8b2a6d913
Revises: a3c9e5f17d42
Create Date: 2026-11-06 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c4e8b2a6d913"
down_revision = "a3c9e5f17d42"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "comments",
        sa.Column("stream_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
    )
    op.add_column(
        "comments",
        sa.Column("hidden_stream_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
    )


def downgrade():
    op.drop_column("comments", "hidden_stream_ids")
    op.drop_column("comments", "stream_ids")
