"""Key crossmatch state by localization as well as event and filter

One GcnEvent can carry several localizations: an EP observation reports each
detected source as its own cone under the shared observation timestamp, and
those cones can be tens of degrees apart. Each is a separate patch of sky to
search, so each needs its own watermark -- previously the service searched only
the most recently created one and silently ignored the rest.

Existing rows are a progress cache for the old single-localization behaviour and
cannot be attributed to a localization after the fact, so they are dropped. The
only cost is one extra sweep per event, which is idempotent.

Revision ID: d4e8b1c07f39
Revises: c8f21a4d90b7
Create Date: 2026-08-15 12:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "d4e8b1c07f39"
down_revision = "c8f21a4d90b7"
branch_labels = None
depends_on = None


def upgrade():
    # Emptying the table lets localization_id be added NOT NULL without
    # inventing an attribution for rows that predate it.
    op.execute("DELETE FROM gcnevent_crossmatch_states")

    op.drop_constraint(
        "gcnevent_crossmatch_states_gcnevent_id_filter_id_key",
        "gcnevent_crossmatch_states",
        type_="unique",
    )
    op.add_column(
        "gcnevent_crossmatch_states",
        sa.Column("localization_id", sa.Integer(), nullable=False),
    )
    op.create_foreign_key(
        "gcnevent_crossmatch_states_localization_id_fkey",
        "gcnevent_crossmatch_states",
        "localizations",
        ["localization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_gcnevent_crossmatch_states_localization_id"),
        "gcnevent_crossmatch_states",
        ["localization_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_gcnevent_crossmatch_states_event_filter_localization",
        "gcnevent_crossmatch_states",
        ["gcnevent_id", "filter_id", "localization_id"],
    )


def downgrade():
    op.execute("DELETE FROM gcnevent_crossmatch_states")

    op.drop_constraint(
        "uq_gcnevent_crossmatch_states_event_filter_localization",
        "gcnevent_crossmatch_states",
        type_="unique",
    )
    # Dropping the column takes its index and foreign key with it.
    op.drop_column("gcnevent_crossmatch_states", "localization_id")
    op.create_unique_constraint(
        "gcnevent_crossmatch_states_gcnevent_id_filter_id_key",
        "gcnevent_crossmatch_states",
        ["gcnevent_id", "filter_id"],
    )
