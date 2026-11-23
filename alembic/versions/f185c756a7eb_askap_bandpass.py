"""ASKAP 943 MHz bandpass

Revision ID: f185c756a7eb
Revises: a6714f2c9d03
Create Date: 2026-11-23 18:00:00.000000

"""

from alembic import op

revision = "f185c756a7eb"
down_revision = "a6714f2c9d03"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'askap-943MHz'")


def downgrade():
    pass
