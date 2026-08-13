"""telescope mpc_obscode

Revision ID: a1c3e5f70b21
Revises: c2b80a6ff0f3
Create Date: 2026-08-13

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1c3e5f70b21"
down_revision = "c2b80a6ff0f3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("telescopes", sa.Column("mpc_obscode", sa.String(), nullable=True))


def downgrade():
    op.drop_column("telescopes", "mpc_obscode")
