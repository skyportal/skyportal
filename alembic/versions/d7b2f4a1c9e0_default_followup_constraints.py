"""default-followup-request trigger constraints

Revision ID: d7b2f4a1c9e0
Revises: c4a7f8e9b2d1
Create Date: 2026-05-31 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "d7b2f4a1c9e0"
down_revision = "c4a7f8e9b2d1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "defaultfollowuprequests",
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "defaultfollowuprequests",
        sa.Column("priority_order", sa.String(), nullable=True),
    )
    op.add_column(
        "defaultfollowuprequests",
        sa.Column("validity_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "defaultfollowuprequests",
        sa.Column("comment", sa.String(), nullable=True),
    )
    op.add_column(
        "defaultfollowuprequests",
        sa.Column("implements_update", sa.Boolean(), nullable=True),
    )


def downgrade():
    op.drop_column("defaultfollowuprequests", "implements_update")
    op.drop_column("defaultfollowuprequests", "comment")
    op.drop_column("defaultfollowuprequests", "validity_days")
    op.drop_column("defaultfollowuprequests", "priority_order")
    op.drop_column("defaultfollowuprequests", "constraints")
