"""Model obj/GCN associations as GcnEventObj with a status enum

Replaces two overlapping mechanisms with one table:

  * ``sourcesconfirmedingcns`` becomes ``gcneventobjs``, and its tri-state
    boolean ``confirmed`` (True/False/NULL) becomes a ``status`` enum, which
    also splits the old NULL into "pending" (awaiting review) and "ambiguous"
    (reviewed, undecided).
  * ``objs.gcn_crossmatch`` -- an array of event dateobs denormalised onto the
    Obj -- is folded into that table as ``pending`` rows and dropped.

The array carried no author, but ``confirmer_id`` is NOT NULL, so backfilled
rows are attributed to the lowest-id System admin (the same convention the
crossmatch service uses when it proposes a row).

Revision ID: c8f21a4d90b7
Revises: a1c3e5f70b21
Create Date: 2026-08-14 17:20:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "c8f21a4d90b7"
down_revision = "a1c3e5f70b21"
branch_labels = None
depends_on = None

STATUSES = ("pending", "confirmed", "ambiguous", "rejected")

OLD_INDEXES = ("created_at", "dateobs", "obj_id")


def _rename_constraints(old, new):
    """Rename every constraint carrying the old table's name."""
    return f"""
        DO $$
        DECLARE c record;
        BEGIN
          FOR c IN SELECT conname FROM pg_constraint
                    WHERE conrelid = '{new}'::regclass
                      AND conname LIKE '{old}%'
          LOOP
            EXECUTE format('ALTER TABLE {new} RENAME CONSTRAINT %I TO %I',
                           c.conname, replace(c.conname, '{old}', '{new}'));
          END LOOP;
        END $$;
    """


def upgrade():
    status_enum = sa.Enum(*STATUSES, name="gcn_event_obj_statuses")
    status_enum.create(op.get_bind(), checkfirst=True)

    op.rename_table("sourcesconfirmedingcns", "gcneventobjs")
    for col in OLD_INDEXES:
        op.execute(
            f"ALTER INDEX IF EXISTS ix_sourcesconfirmedingcns_{col} "
            f"RENAME TO ix_gcneventobjs_{col}"
        )
    # RENAME TABLE leaves constraints and the id sequence under the old name.
    op.execute(_rename_constraints("sourcesconfirmedingcns", "gcneventobjs"))
    op.execute(
        "ALTER SEQUENCE IF EXISTS sourcesconfirmedingcns_id_seq "
        "RENAME TO gcneventobjs_id_seq"
    )

    # Nullable first so existing rows can be mapped before the constraint lands.
    op.add_column("gcneventobjs", sa.Column("status", status_enum, nullable=True))
    # NULL was written both by the crossmatch (never reviewed) and by the old
    # "ambiguous" button (reviewed, undecided), and the two are indistinguishable
    # here. Mapping to 'pending' re-queues the handful of ambiguous verdicts for
    # one more look; mapping the other way would silently mark unreviewed
    # proposals as reviewed and drop them out of the scanning queue.
    op.execute(
        """
        UPDATE gcneventobjs SET status = CASE
            WHEN confirmed IS TRUE THEN 'confirmed'::gcn_event_obj_statuses
            WHEN confirmed IS FALSE THEN 'rejected'::gcn_event_obj_statuses
            ELSE 'pending'::gcn_event_obj_statuses
        END
        """
    )
    op.alter_column("gcneventobjs", "status", nullable=False)
    op.execute("ALTER TABLE gcneventobjs ALTER COLUMN status SET DEFAULT 'pending'")
    op.create_index(op.f("ix_gcneventobjs_status"), "gcneventobjs", ["status"])
    op.drop_column("gcneventobjs", "confirmed")

    # Fold objs.gcn_crossmatch in. Only entries that parse as a timestamp and
    # match a real event are kept: the array was free-form text with no FK, so
    # it can contain values no gcnevent corresponds to.
    op.execute(
        """
        INSERT INTO gcneventobjs
            (obj_id, dateobs, status, confirmer_id, created_at, modified)
        SELECT DISTINCT o.id,
               e.dateobs,
               'pending'::gcn_event_obj_statuses,
               (SELECT u.id FROM users u
                  JOIN user_acls ua ON ua.user_id = u.id
                 WHERE ua.acl_id = 'System admin'
                 ORDER BY u.id LIMIT 1),
               now(),
               now()
          FROM objs o
          CROSS JOIN LATERAL unnest(o.gcn_crossmatch) AS raw(dateobs_text)
          JOIN gcnevents e
            ON e.dateobs = (
                 CASE WHEN raw.dateobs_text ~
                      '^\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}'
                      THEN raw.dateobs_text::timestamp END)
         WHERE o.gcn_crossmatch IS NOT NULL
           AND EXISTS (SELECT 1 FROM users u
                         JOIN user_acls ua ON ua.user_id = u.id
                        WHERE ua.acl_id = 'System admin')
           AND NOT EXISTS (
                 SELECT 1 FROM gcneventobjs g
                  WHERE g.obj_id = o.id AND g.dateobs = e.dateobs)
        """
    )
    op.drop_column("objs", "gcn_crossmatch")


def downgrade():
    op.add_column("objs", sa.Column("gcn_crossmatch", sa.ARRAY(sa.String())))
    # Confirmed associations are what the array held; pending/rejected had no
    # representation in it.
    op.execute(
        """
        UPDATE objs SET gcn_crossmatch = sub.dateobs_list
          FROM (
            SELECT obj_id,
                   array_agg(to_char(dateobs, 'YYYY-MM-DD HH24:MI:SS')) AS dateobs_list
              FROM gcneventobjs
             WHERE status = 'confirmed'
             GROUP BY obj_id
          ) AS sub
         WHERE objs.id = sub.obj_id
        """
    )

    op.add_column("gcneventobjs", sa.Column("confirmed", sa.Boolean(), nullable=True))
    op.execute(
        """
        UPDATE gcneventobjs SET confirmed = CASE
            WHEN status = 'confirmed' THEN TRUE
            WHEN status = 'rejected' THEN FALSE
            ELSE NULL
        END
        """
    )
    op.drop_index(op.f("ix_gcneventobjs_status"), table_name="gcneventobjs")
    op.drop_column("gcneventobjs", "status")

    for col in OLD_INDEXES:
        op.execute(
            f"ALTER INDEX IF EXISTS ix_gcneventobjs_{col} "
            f"RENAME TO ix_sourcesconfirmedingcns_{col}"
        )
    op.execute(
        "ALTER SEQUENCE IF EXISTS gcneventobjs_id_seq "
        "RENAME TO sourcesconfirmedingcns_id_seq"
    )
    op.rename_table("gcneventobjs", "sourcesconfirmedingcns")
    # after the rename: the helper addresses the table by its new name
    op.execute(_rename_constraints("gcneventobjs", "sourcesconfirmedingcns"))

    sa.Enum(name="gcn_event_obj_statuses").drop(op.get_bind(), checkfirst=True)
