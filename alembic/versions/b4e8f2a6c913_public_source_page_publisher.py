"""Record who published a public source page

Revision ID: b4e8f2a6c913
Revises: d7b3e9f41a26
Create Date: 2026-11-24 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "b4e8f2a6c913"
down_revision = "d7b3e9f41a26"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "publicsourcepages",
        sa.Column("created_by_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_publicsourcepages_created_by_id"),
        "publicsourcepages",
        ["created_by_id"],
        unique=False,
    )
    op.create_foreign_key(
        "publicsourcepages_created_by_id_fkey",
        "publicsourcepages",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "publicsourcepages_created_by_id_fkey",
        "publicsourcepages",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_publicsourcepages_created_by_id"), table_name="publicsourcepages"
    )
    op.drop_column("publicsourcepages", "created_by_id")
