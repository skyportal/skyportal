"""instance managers

Revision ID: c4e7a2b9d1f3
Revises: d4a7b91c6e52
Create Date: 2026-10-27

"""

import sqlalchemy as sa

from alembic import op

revision = "c4e7a2b9d1f3"
down_revision = "d4a7b91c6e52"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "instance_managers",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("show_email", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_instance_managers_created_at"),
        "instance_managers",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instance_managers_user_id"),
        "instance_managers",
        ["user_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(op.f("ix_instance_managers_user_id"), table_name="instance_managers")
    op.drop_index(
        op.f("ix_instance_managers_created_at"), table_name="instance_managers"
    )
    op.drop_table("instance_managers")
