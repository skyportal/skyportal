"""Add groups.discoverable_data

Revision ID: d7e5b2a91c46
Revises: c8a4f1d92b73
Create Date: 2026-08-25 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d7e5b2a91c46"
down_revision = "c8a4f1d92b73"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "groups",
        sa.Column(
            "discoverable_data",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade():
    op.drop_column("groups", "discoverable_data")
