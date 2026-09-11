"""Track whether the one-shot archival crossmatch pass has run

Revision ID: e7c94b2d1a63
Revises: d5b82a1c7e40
Create Date: 2026-08-08 13:20:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e7c94b2d1a63"
down_revision = "d5b82a1c7e40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "gcnevent_crossmatch_states",
        sa.Column(
            "archival_done", sa.Boolean(), server_default="false", nullable=False
        ),
    )


def downgrade():
    op.drop_column("gcnevent_crossmatch_states", "archival_done")
