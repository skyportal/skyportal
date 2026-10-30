"""broker credential stream epoch

Revision ID: d4a7b91c6e52
Revises: e3c8a7b45d19
Create Date: 2026-10-29 07:10:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4a7b91c6e52"
down_revision = "e3c8a7b45d19"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "brokercredentials",
        sa.Column("stream_epoch", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("brokercredentials", "stream_epoch")
