"""Add atlasc and atlaso bandpasses

Revision ID: aea51b4ff0b0
Revises: f9611048498a
Create Date: 2022-01-23 23:11:31.441589

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "aea51b4ff0b0"
down_revision = "d61a8bea7313"
branch_labels = None
depends_on = None


def upgrade():
    # add atlasc and atlaco
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'atlasc'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'atlaso'")


def downgrade():
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
