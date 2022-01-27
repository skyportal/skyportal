"""slack trigger api

Revision ID: 82f5a89fbe59
Revises: d61a8bea7313
Create Date: 2022-01-26 21:06:14.272254

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '82f5a89fbe59'
down_revision = 'd61a8bea7313'
branch_labels = None
depends_on = None


def upgrade():
    # add atlasc and atlaso to bandpasses, ATLASAPI to followup_apis
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'SWIFTAPI'")


def downgrade():
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
