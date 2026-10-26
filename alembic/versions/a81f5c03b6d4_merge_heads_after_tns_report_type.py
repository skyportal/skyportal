"""merge 09275d, 9e5f53 and 27112b

Three branches each added a migration straight onto e7f3b9d21a08, leaving
alembic with three heads. Nothing here changes the schema; the revision exists
to join them so there is one head again.

Revision ID: a81f5c03b6d4
Revises: 09275d149261, 9e5f53967a6a, 27112bd74c13
Create Date: 2026-10-26 07:05:00.000000

"""

# revision identifiers, used by Alembic.
revision = "a81f5c03b6d4"
down_revision = ("09275d149261", "9e5f53967a6a", "27112bd74c13")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
