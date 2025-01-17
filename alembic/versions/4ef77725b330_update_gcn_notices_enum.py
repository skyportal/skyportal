"""Update GCN notices enum

Revision ID: 4ef77725b330
Revises: 1f4da189227e
Create Date: 2021-07-23 17:30:16.102665

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4ef77725b330"
down_revision = "1f4da189227e"
branch_labels = None
depends_on = None


def upgrade():
    # Add new values to the GCN noticetype ENUM type
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE noticetype ADD VALUE IF NOT EXISTS 'SK_SN' BEFORE 'ICECUBE_CASCADE'"
        )


def downgrade():
    # There is no action taken to downgrade this migration.
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
