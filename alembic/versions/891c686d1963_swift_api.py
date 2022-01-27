"""swift api

Revision ID: 891c686d1963
Revises: d61a8bea7313
Create Date: 2022-01-26 21:20:05.479694

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '891c686d1963'
down_revision = 'd61a8bea7313'
branch_labels = None
depends_on = None


def upgrade():
    # add UVOTXRTAPI to followup_apis
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'UVOTXRTAPI'")


def downgrade():
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
