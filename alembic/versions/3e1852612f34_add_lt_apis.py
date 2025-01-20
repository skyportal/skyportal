"""Add LT APIs

Revision ID: 3e1852612f34
Revises: c1354c411fab
Create Date: 2021-02-25 19:10:55.114202

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "3e1852612f34"
down_revision = "c1354c411fab"
branch_labels = None
depends_on = None


def upgrade():
    # Add new Liverpool Telescope API values to the followup_apis ENUM type
    # Logic adapted from https://medium.com/makimo-tech-blog/upgrading-postgresqls-enum-type-with-sqlalchemy-using-alembic-migration-881af1e30abe
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'IOOAPI'")
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'IOIAPI'")
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'SPRATAPI'")


def downgrade():
    # There is no action taken to downgrade this migration.
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
