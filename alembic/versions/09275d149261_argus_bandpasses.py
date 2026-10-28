"""Argus bandpasses

Revision ID: 09275d149261
Revises: e7f3b9d21a08
Create Date: 2026-10-14 01:45:14.000000

"""

from alembic import op

revision = "09275d149261"
down_revision = "e7f3b9d21a08"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'argusbeta'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'argusrho'")


def downgrade():
    pass
