"""public page origin and filter

Revision ID: b2f7c1a94d33
Revises: c7d1a4e9f3b2
Create Date: 2026-08-12 09:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b2f7c1a94d33"
down_revision = "c7d1a4e9f3b2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "publicsourcepages",
        sa.Column("origin", sa.String(), nullable=False, server_default="source"),
    )
    op.add_column(
        "publicsourcepages", sa.Column("filter_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f("ix_publicsourcepages_filter_id"),
        "publicsourcepages",
        ["filter_id"],
        unique=False,
    )
    op.create_foreign_key(
        "publicsourcepages_filter_id_fkey",
        "publicsourcepages",
        "filters",
        ["filter_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "publicsourcepages_filter_id_fkey", "publicsourcepages", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_publicsourcepages_filter_id"), table_name="publicsourcepages"
    )
    op.drop_column("publicsourcepages", "filter_id")
    op.drop_column("publicsourcepages", "origin")
