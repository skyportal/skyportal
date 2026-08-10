"""Per-(event, broker) state for the GCN alert crossmatch service

Revision ID: d5b82a1c7e40
Revises: c3a71f0e5d92
Create Date: 2026-08-08 11:55:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d5b82a1c7e40"
down_revision = "c3a71f0e5d92"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gcnevent_crossmatch_states",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gcnevent_id", sa.Integer(), nullable=False),
        sa.Column("broker_id", sa.Integer(), nullable=False),
        sa.Column("last_queried", sa.DateTime(), nullable=True),
        sa.Column("last_alert_jd", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("n_matches", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["gcnevent_id"], ["gcnevents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["broker_id"], ["brokers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gcnevent_id", "broker_id"),
    )
    op.create_index(
        op.f("ix_gcnevent_crossmatch_states_created_at"),
        "gcnevent_crossmatch_states",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gcnevent_crossmatch_states_gcnevent_id"),
        "gcnevent_crossmatch_states",
        ["gcnevent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gcnevent_crossmatch_states_broker_id"),
        "gcnevent_crossmatch_states",
        ["broker_id"],
        unique=False,
    )
    # the service's hot query is "which rows are due to run next", i.e. a filter
    # on status combined with an ordering on last_queried
    op.create_index(
        op.f("ix_gcnevent_crossmatch_states_status"),
        "gcnevent_crossmatch_states",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gcnevent_crossmatch_states_last_queried"),
        "gcnevent_crossmatch_states",
        ["last_queried"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_gcnevent_crossmatch_states_last_queried"),
        table_name="gcnevent_crossmatch_states",
    )
    op.drop_index(
        op.f("ix_gcnevent_crossmatch_states_status"),
        table_name="gcnevent_crossmatch_states",
    )
    op.drop_index(
        op.f("ix_gcnevent_crossmatch_states_broker_id"),
        table_name="gcnevent_crossmatch_states",
    )
    op.drop_index(
        op.f("ix_gcnevent_crossmatch_states_gcnevent_id"),
        table_name="gcnevent_crossmatch_states",
    )
    op.drop_index(
        op.f("ix_gcnevent_crossmatch_states_created_at"),
        table_name="gcnevent_crossmatch_states",
    )
    op.drop_table("gcnevent_crossmatch_states")
