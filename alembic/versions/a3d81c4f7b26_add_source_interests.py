"""Add source_interests table and system comments

Revision ID: a3d81c4f7b26
Revises: d4c17b9e5a02
Create Date: 2026-08-05 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a3d81c4f7b26"
down_revision = "d4c17b9e5a02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "source_interests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("obj_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("link", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["obj_id"], ["objs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("created_at", "obj_id", "user_id"):
        op.create_index(
            op.f(f"ix_source_interests_{column}"),
            "source_interests",
            [column],
            unique=False,
        )

    op.add_column(
        "comments",
        sa.Column(
            "system", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )


def downgrade():
    op.drop_column("comments", "system")
    op.drop_table("source_interests")
