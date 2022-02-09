"""Migration for sncosmo 2.5 -> 2.7

Revision ID: 5208fe393e57
Revises: 82f5a89fbe59
Create Date: 2022-02-09 18:40:38.616257

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '5208fe393e57'
down_revision = '82f5a89fbe59'
branch_labels = None
depends_on = None


def upgrade():
    # add bandpasses added between 2.5 and 2.7
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'f062'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'f087'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'f106'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'f129'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'f146'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'f158'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'f184'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'f213'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'ps1::g'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'ps1::r'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'ps1::i'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'ps1::z'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'ps1::y'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'ps1::open'")
        op.execute("ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS 'ps1::w'")


def downgrade():
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
