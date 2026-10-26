"""Default observer for an instrument's TNS reports

Adds instruments.default_observer. It is nullable and defaults to nothing, so
an instrument that records its observers keeps crediting them; only a robotic
instrument, whose spectra name no observer, needs one set.

Revision ID: c4e9b2a71f08
Revises: 9e5f53967a6a
Create Date: 2026-10-26 06:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c4e9b2a71f08"
down_revision = "9e5f53967a6a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "instruments",
        sa.Column("default_observer", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_column("instruments", "default_observer")
