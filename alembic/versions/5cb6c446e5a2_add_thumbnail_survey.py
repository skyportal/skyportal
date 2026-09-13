"""Add thumbnail survey

Revision ID: 5cb6c446e5a2
Revises: c2b80a6ff0f3
Create Date: 2026-08-14 16:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5cb6c446e5a2"
down_revision = "c2b80a6ff0f3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("thumbnails", sa.Column("survey", sa.String(), nullable=True))


def downgrade():
    op.drop_column("thumbnails", "survey")
