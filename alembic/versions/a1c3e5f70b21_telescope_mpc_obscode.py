"""telescope mpc_obscode

Revision ID: a1c3e5f70b21
Revises: 5cb6c446e5a2
Create Date: 2026-08-13

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1c3e5f70b21"
down_revision = "5cb6c446e5a2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("telescopes", sa.Column("mpc_obscode", sa.String(), nullable=True))


def downgrade():
    op.drop_column("telescopes", "mpc_obscode")
