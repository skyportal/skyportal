"""Group-scoped read access for GCN events

Creates the group_gcnevents join table and backfills every existing GcnEvent
into the sitewide public group.

The backfill is required, not cosmetic: GcnEvent.read is now
accessible_by_groups_members, so an event with no rows in this table is
invisible to everyone but system admins. Every event that exists today was
readable by all users, so all of them are attached to the public group to
preserve that behavior. Only newly ingested proprietary events (e.g. the
Einstein Probe unverified-candidate stream) are attached to narrower groups.

Revision ID: c3a71f0e5d92
Revises: 87b838c05b25
Create Date: 2026-08-08 08:30:00.000000

"""

import sqlalchemy as sa

from alembic import op
from baselayer.app.env import load_env

# revision identifiers, used by Alembic.
revision = "c3a71f0e5d92"
down_revision = "87b838c05b25"
branch_labels = None
depends_on = None

_, cfg = load_env()


def upgrade():
    op.create_table(
        "group_gcnevents",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("gcnevent_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gcnevent_id"], ["gcnevents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "group_gcnevents_forward_ind",
        "group_gcnevents",
        ["group_id", "gcnevent_id"],
        unique=True,
    )
    op.create_index(
        "group_gcnevents_reverse_ind",
        "group_gcnevents",
        ["gcnevent_id", "group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_group_gcnevents_created_at"),
        "group_gcnevents",
        ["created_at"],
        unique=False,
    )

    public_group_name = cfg["misc"]["public_group_name"]

    conn = op.get_bind()

    event_count = conn.execute(sa.text("SELECT count(*) FROM gcnevents")).scalar()
    public_group_id = conn.execute(
        sa.text("SELECT id FROM groups WHERE name = :name"),
        {"name": public_group_name},
    ).scalar()

    # Fail loudly rather than orphan the entire GCN history. Without a public
    # group to attach them to, the backfill below is a silent no-op and every
    # pre-existing event becomes unreadable by every non-admin user -- with no
    # error to explain why the GCN pages suddenly went empty.
    if event_count and public_group_id is None:
        raise RuntimeError(
            f"Cannot backfill GCN event access: no group named "
            f"{public_group_name!r} (misc.public_group_name) exists, but "
            f"{event_count} GcnEvent(s) are present. Create that group, or "
            f"correct misc.public_group_name, before running this migration."
        )

    # Backfill: attach every pre-existing event to the sitewide public group so
    # that this migration is behavior-preserving for existing data.
    if event_count:
        op.execute(
            sa.text(
                """
                INSERT INTO group_gcnevents (created_at, modified, group_id, gcnevent_id)
                SELECT now(), now(), :group_id, e.id
                FROM gcnevents e
                ON CONFLICT DO NOTHING
                """
            ).bindparams(group_id=public_group_id)
        )


def downgrade():
    op.drop_index(op.f("ix_group_gcnevents_created_at"), table_name="group_gcnevents")
    op.drop_index("group_gcnevents_reverse_ind", table_name="group_gcnevents")
    op.drop_index("group_gcnevents_forward_ind", table_name="group_gcnevents")
    op.drop_table("group_gcnevents")
