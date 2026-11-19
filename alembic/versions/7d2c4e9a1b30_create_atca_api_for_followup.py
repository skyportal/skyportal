"""Create ATCA rapid response API for followup

Revision ID: 7d2c4e9a1b30
Revises: 02d239a276d5
Create Date: 2026-11-19 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7d2c4e9a1b30"
down_revision = "02d239a276d5"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'ATCAAPI'")


def downgrade():
    pass
