"""Add LCO APIs

Revision ID: c0e0173c90b0
Revises: 0595e877f471
Create Date: 2021-05-10 18:10:30.835781

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c0e0173c90b0'
down_revision = '0baa156cdd5b'
branch_labels = None
depends_on = None


def upgrade():
    # Add new LCO API values to the followup_apis ENUM type
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'SINISTROAPI'")
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'SPECTRALAPI'")
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'FLOYDSAPI'")
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'MUSCATAPI'")


def downgrade():
    # There is no action taken to downgrade this migration.
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
