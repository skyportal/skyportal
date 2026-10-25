"""Keep an object off TNS

Adds objs.withhold_from_tns. It defaults to false, so every existing object
keeps its current behaviour and nothing that was shareable stops being
shareable.

Revision ID: f2a6c81d57b3
Revises: e7f3b9d21a08
Create Date: 2026-10-25 13:45:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f2a6c81d57b3"
down_revision = "e7f3b9d21a08"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "objs",
        sa.Column(
            "withhold_from_tns",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade():
    op.drop_column("objs", "withhold_from_tns")
