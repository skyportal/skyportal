"""channel and system on every comment table

Revision ID: c7a2e8b41d63
Revises: d3f7a1b9c204
Create Date: 2026-09-03

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c7a2e8b41d63"
down_revision = "d3f7a1b9c204"
branch_labels = None
depends_on = None

# comments already has both columns; the rest inherit them from CommentMixin.
TABLES = (
    "comments_on_spectra",
    "comments_on_gcns",
    "comments_on_earthquakes",
    "comments_on_shifts",
)


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("channel", sa.String(), nullable=True))
        op.create_index(f"ix_{table}_channel", table, ["channel"], unique=False)
        op.add_column(
            table,
            sa.Column(
                "system", sa.Boolean(), nullable=False, server_default=sa.text("false")
            ),
        )


def downgrade():
    for table in TABLES:
        op.drop_column(table, "system")
        op.drop_index(f"ix_{table}_channel", table_name=table)
        op.drop_column(table, "channel")
