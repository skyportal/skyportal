"""filter autosave

Revision ID: 87b838c05b25
Revises: b7e1f4a90c31
Create Date: 2026-08-06 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "87b838c05b25"
down_revision = "b7e1f4a90c31"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "filters",
        sa.Column(
            "autosave",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade():
    op.drop_column("filters", "autosave")
