"""broker default_photometry

Revision ID: c3a8f1d27b94
Revises: a3f7d21c8b45
Create Date: 2026-09-07

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3a8f1d27b94"
down_revision = "a3f7d21c8b45"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "brokers",
        sa.Column(
            "default_photometry", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.create_index(
        "brokers_default_photometry",
        "brokers",
        ["default_photometry"],
        unique=True,
        postgresql_where=sa.text("default_photometry"),
    )


def downgrade():
    op.drop_index("brokers_default_photometry", table_name="brokers")
    op.drop_column("brokers", "default_photometry")
