"""Test migration

Revision ID: ac4dbd89b698
Revises: d61a8bea7313
Create Date: 2022-01-26 21:23:15.248440

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'ac4dbd89b698'
down_revision = 'd61a8bea7313'
branch_labels = None
depends_on = None


def upgrade():
    # add atlasc and atlaso to bandpasses, ATLASAPI to followup_apis
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'atlasc'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'atlaso'")
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'ATLASAPI'")


def downgrade():
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
