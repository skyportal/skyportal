"""Group-scoped read access for observing runs

Creates the group_observingruns join table and backfills every existing
ObservingRun into the sitewide public group.

The backfill is required, not cosmetic: ObservingRun.read is now
accessible_by_groups_members, so a run with no rows in this table is invisible
to everyone but system admins -- and ClassicalAssignment.read depends on the
run, so its target list would vanish with it. Every run that exists today was
world-readable, so all of them are attached to the public group to preserve
that behavior. A group that wants its plans private narrows the run afterwards.

Revision ID: f1c4e7a92b60
Revises: c7f41a9e2b58
Create Date: 2026-08-27 13:40:00.000000

"""

import sqlalchemy as sa

from alembic import op
from baselayer.app.env import load_env

# revision identifiers, used by Alembic.
revision = "f1c4e7a92b60"
down_revision = "c7f41a9e2b58"
branch_labels = None
depends_on = None

_, cfg = load_env()


def upgrade():
    op.create_table(
        "group_observingruns",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("observingrun_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["observingrun_id"], ["observingruns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "group_observingruns_forward_ind",
        "group_observingruns",
        ["group_id", "observingrun_id"],
        unique=True,
    )
    op.create_index(
        "group_observingruns_reverse_ind",
        "group_observingruns",
        ["observingrun_id", "group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_group_observingruns_created_at"),
        "group_observingruns",
        ["created_at"],
        unique=False,
    )

    public_group_name = cfg["misc"]["public_group_name"]

    conn = op.get_bind()

    run_count = conn.execute(sa.text("SELECT count(*) FROM observingruns")).scalar()
    public_group_id = conn.execute(
        sa.text("SELECT id FROM groups WHERE name = :name"),
        {"name": public_group_name},
    ).scalar()

    # Fail loudly rather than orphan every observing run. Without a public
    # group to attach them to, the backfill below is a silent no-op and every
    # pre-existing run becomes unreadable by every non-admin user -- with no
    # error to explain why the observing run pages suddenly went empty.
    if run_count and public_group_id is None:
        raise RuntimeError(
            f"Cannot backfill observing run access: no group named "
            f"{public_group_name!r} (misc.public_group_name) exists, but "
            f"{run_count} ObservingRun(s) are present. Create that group, or "
            f"correct misc.public_group_name, before running this migration."
        )

    # Backfill: attach every pre-existing run to the sitewide public group so
    # that this migration is behavior-preserving for existing data.
    if run_count:
        op.execute(
            sa.text(
                """
                INSERT INTO group_observingruns (created_at, modified, group_id, observingrun_id)
                SELECT now(), now(), :group_id, r.id
                FROM observingruns r
                ON CONFLICT DO NOTHING
                """
            ).bindparams(group_id=public_group_id)
        )


def downgrade():
    op.drop_index(
        op.f("ix_group_observingruns_created_at"), table_name="group_observingruns"
    )
    op.drop_index("group_observingruns_reverse_ind", table_name="group_observingruns")
    op.drop_index("group_observingruns_forward_ind", table_name="group_observingruns")
    op.drop_table("group_observingruns")
