"""Cache ADS paper matches by object.

Revision ID: 91c2e8a4b70f
Revises: c4f1e8a2b937
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "91c2e8a4b70f"
down_revision = "c4f1e8a2b937"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "paper_corner_cache",
        sa.Column(
            "obj_id",
            sa.String(),
            sa.ForeignKey("objs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("tns_name", sa.String(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("matches", JSONB(), nullable=False),
    )


def downgrade():
    op.drop_table("paper_corner_cache")
