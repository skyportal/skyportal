"""gemini_api

Revision ID: 3eb663b5c3e0
Revises: fcc48485cb52
Create Date: 2024-10-02 17:31:56.759818

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "3eb663b5c3e0"
down_revision = "fcc48485cb52"
branch_labels = None
depends_on = None


def upgrade():
    # Add new Gemini API value to the followup_apis ENUM type
    # Logic adapted from https://medium.com/makimo-tech-blog/upgrading-postgresqls-enum-type-with-sqlalchemy-using-alembic-migration-881af1e30abe
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'GEMINIAPI'")


def downgrade():
    # There is no action taken to downgrade this migration.
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
