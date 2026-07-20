"""instrument across_id

Revision ID: a1c0ss1d0001
Revises: c8d1e9f4a2b7
Create Date: 2026-07-15 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1c0ss1d0001"
down_revision = "c8d1e9f4a2b7"
branch_labels = None
depends_on = None


def upgrade():
    # NASA ACROSS instrument UUID; routes visibility to the ACROSS calculator.
    op.add_column("instruments", sa.Column("across_id", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_instruments_across_id"), "instruments", ["across_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_instruments_across_id"), table_name="instruments")
    op.drop_column("instruments", "across_id")
