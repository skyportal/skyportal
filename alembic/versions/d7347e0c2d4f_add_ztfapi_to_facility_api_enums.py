"""Add ZTFAPI to facility API enums

Revision ID: d7347e0c2d4f
Revises: 5efdda259fd0
Create Date: 2021-05-19 11:09:54.951386

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'd7347e0c2d4f'
down_revision = '5efdda259fd0'
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'ZTFAPI'")


def downgrade():
    # There is no action taken to downgrade this migration.
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
