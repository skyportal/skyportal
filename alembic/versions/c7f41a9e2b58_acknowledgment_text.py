"""telescope and instrument acknowledgment text

Revision ID: c7f41a9e2b58
Revises: a7c94e1d6b30
Create Date: 2026-08-25

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c7f41a9e2b58"
down_revision = "d7e5b2a91c46"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("telescopes", sa.Column("acknowledgment", sa.String(), nullable=True))
    op.add_column(
        "instruments", sa.Column("acknowledgment", sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column("instruments", "acknowledgment")
    op.drop_column("telescopes", "acknowledgment")
