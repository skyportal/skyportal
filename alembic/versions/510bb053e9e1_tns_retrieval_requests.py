"""tns retrieval requests

Revision ID: 510bb053e9e1
Revises: b4e8f2a6c913
Create Date: 2026-11-24

"""

import sqlalchemy as sa

from alembic import op

revision = "510bb053e9e1"
down_revision = "b4e8f2a6c913"
branch_labels = None
depends_on = None

INDEXED_COLUMNS = ("created_at", "obj_id", "status", "user_id")


def upgrade():
    op.create_table(
        "tnsretrievalrequests",
        sa.Column("obj_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["obj_id"], ["objs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in INDEXED_COLUMNS:
        op.create_index(
            op.f(f"ix_tnsretrievalrequests_{column}"),
            "tnsretrievalrequests",
            [column],
            unique=False,
        )


def downgrade():
    for column in INDEXED_COLUMNS:
        op.drop_index(
            op.f(f"ix_tnsretrievalrequests_{column}"),
            table_name="tnsretrievalrequests",
        )
    op.drop_table("tnsretrievalrequests")
