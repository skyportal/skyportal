"""Key crossmatch state by filter rather than broker

A filter carries its own broker, survey, permissions and audience, so it -- not
the broker -- is the unit of crossmatch configuration. Two filters on one broker
(e.g. ZTF and LSST) must progress independently; sharing a broker-keyed row made
them clobber each other's watermark and archival flag.

Existing rows are a progress cache for the old single-filter configuration and
cannot be mapped to a filter unambiguously, so they are dropped. The only cost
is one extra sweep per event, which is idempotent.

Revision ID: a4d17c3b8e52
Revises: e7c94b2d1a63
Create Date: 2026-08-10 16:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "a4d17c3b8e52"
down_revision = "e7c94b2d1a63"
branch_labels = None
depends_on = None


def upgrade():
    # The rows are a progress cache for the old single-filter configuration and
    # cannot be mapped onto a filter unambiguously. Emptying the table also lets
    # filter_id be added NOT NULL without inventing a default.
    op.execute("DELETE FROM gcnevent_crossmatch_states")

    # Dropping the column takes its index, foreign key and the
    # (gcnevent_id, broker_id) unique constraint with it.
    op.drop_column("gcnevent_crossmatch_states", "broker_id")

    op.add_column(
        "gcnevent_crossmatch_states",
        sa.Column("filter_id", sa.Integer(), nullable=False),
    )
    op.create_foreign_key(
        "gcnevent_crossmatch_states_filter_id_fkey",
        "gcnevent_crossmatch_states",
        "filters",
        ["filter_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_gcnevent_crossmatch_states_filter_id"),
        "gcnevent_crossmatch_states",
        ["filter_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "gcnevent_crossmatch_states_gcnevent_id_filter_id_key",
        "gcnevent_crossmatch_states",
        ["gcnevent_id", "filter_id"],
    )


def downgrade():
    op.execute("DELETE FROM gcnevent_crossmatch_states")
    op.drop_column("gcnevent_crossmatch_states", "filter_id")
    op.add_column(
        "gcnevent_crossmatch_states",
        sa.Column("broker_id", sa.Integer(), nullable=False),
    )
    op.create_foreign_key(
        "gcnevent_crossmatch_states_broker_id_fkey",
        "gcnevent_crossmatch_states",
        "brokers",
        ["broker_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_gcnevent_crossmatch_states_broker_id"),
        "gcnevent_crossmatch_states",
        ["broker_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "gcnevent_crossmatch_states_gcnevent_id_broker_id_key",
        "gcnevent_crossmatch_states",
        ["gcnevent_id", "broker_id"],
    )
