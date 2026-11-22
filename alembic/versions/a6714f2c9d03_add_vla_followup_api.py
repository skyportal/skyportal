"""Add the VLA follow-up API

Revision ID: a6714f2c9d03
Revises: c4f1e8a2b937
"""

from alembic import op

revision = "a6714f2c9d03"
down_revision = "c4f1e8a2b937"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'VLAAPI'")


def downgrade():
    pass
