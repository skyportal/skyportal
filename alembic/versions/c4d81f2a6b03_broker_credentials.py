"""Per-user broker credentials

A user's upstream account (e.g. a Lasair account owning private filters) is
personal, so it cannot live in the admin-owned ``brokers.altdata``.

Revision ID: c4d81f2a6b03
Revises: a3f7d21c8b45
Create Date: 2026-09-11

"""

import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "c4d81f2a6b03"
down_revision = "a3f7d21c8b45"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "brokercredentials",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("broker_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "topics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "topic_filter_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "_altdata",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=True,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["broker_id"], ["brokers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("broker_id", "user_id"),
    )
    op.create_index(
        op.f("ix_brokercredentials_created_at"),
        "brokercredentials",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_brokercredentials_broker_id"),
        "brokercredentials",
        ["broker_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_brokercredentials_user_id"),
        "brokercredentials",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_brokercredentials_user_id"), table_name="brokercredentials")
    op.drop_index(
        op.f("ix_brokercredentials_broker_id"), table_name="brokercredentials"
    )
    op.drop_index(
        op.f("ix_brokercredentials_created_at"), table_name="brokercredentials"
    )
    op.drop_table("brokercredentials")
