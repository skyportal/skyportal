"""broker ingest flag

Ingestion used to follow `active`, which also gates every on-demand call, so
activating a broker to search its alerts subscribed the instance to its stream.
Existing rows keep that behaviour: the flag is backfilled from `active`.

Revision ID: c9e4b7a21f68
Revises: d4e5f6a7b8c9
Create Date: 2026-09-22

"""

import sqlalchemy as sa

from alembic import op

revision = "c9e4b7a21f68"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "brokers",
        sa.Column(
            "ingest", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.execute("UPDATE brokers SET ingest = active")


def downgrade():
    op.drop_column("brokers", "ingest")
