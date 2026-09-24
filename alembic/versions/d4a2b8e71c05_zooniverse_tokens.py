"""zooniverse tokens

Revision ID: d4a2b8e71c05
Revises: c7d1a4e9f3b2
Create Date: 2026-08-12 21:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4a2b8e71c05"
down_revision = "c7d1a4e9f3b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "zooniversetokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("zooniverse_user_id", sa.String(), nullable=True),
        sa.Column("zooniverse_login", sa.String(), nullable=True),
        sa.Column("access_token", sa.String(), nullable=False),
        sa.Column("refresh_token", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_zooniversetokens_created_at"),
        "zooniversetokens",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_zooniversetokens_user_id"),
        "zooniversetokens",
        ["user_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(op.f("ix_zooniversetokens_user_id"), table_name="zooniversetokens")
    op.drop_index(op.f("ix_zooniversetokens_created_at"), table_name="zooniversetokens")
    op.drop_table("zooniversetokens")
