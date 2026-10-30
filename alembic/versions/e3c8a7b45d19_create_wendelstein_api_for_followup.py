"""Create Wendelstein instrument API for followup

Revision ID: e3c8a7b45d19
Revises: d9d858453a23
Create Date: 2026-10-29 09:45:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e3c8a7b45d19"
down_revision = "d9d858453a23"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'WENDELSTEINAPI'")


def downgrade():
    pass
