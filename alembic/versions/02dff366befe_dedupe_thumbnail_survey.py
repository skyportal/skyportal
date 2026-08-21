"""dedupe thumbnail survey

Revision ID: 02dff366befe
Revises: a3d81c4f7b26
Create Date: 2026-08-18

Backfills survey on legacy new/ref/sub rows from their most recent
same-obj/type sibling (a NULL row with no such sibling is left alone),
dedupes any remaining (obj_id, type, survey) duplicates table-wide, and
adds a unique constraint to enforce one thumbnail per survey going
forward. Batched delete + CONCURRENTLY index build to avoid a table-wide
lock (see 3d9f7a1c2b45 for the same pattern). Fixes duplicate ZTF tiles
on the source page.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "02dff366befe"
down_revision = "a3d81c4f7b26"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "thumbnails_obj_id_type_survey_key"
DELETE_BATCH_SIZE = 5000


def upgrade():
    # DISTINCT ON picks one deterministic sibling (the most recent) per
    # obj_id/type: a plain self-join here left the choice up to Postgres when
    # an obj/type had siblings on two different surveys.
    op.execute(
        """
        UPDATE thumbnails t
        SET survey = pick.survey
        FROM (
            SELECT DISTINCT ON (obj_id, type) obj_id, type, survey
            FROM thumbnails
            WHERE survey IS NOT NULL
            ORDER BY obj_id, type, created_at DESC, id DESC
        ) pick
        WHERE t.obj_id = pick.obj_id
          AND t.type = pick.type
          AND t.survey IS NULL
          AND t.type IN ('new', 'ref', 'sub')
        """
    )

    conn = op.get_bind()
    with op.get_context().autocommit_block():
        # Keep the most recent row per (obj_id, type, survey); the file on disk
        # is untouched by this raw delete. Batched so this doesn't hold one
        # long-running lock across the whole table.
        delete_stmt = sa.text(
            f"""
            DELETE FROM thumbnails
            WHERE ctid IN (
                SELECT t.ctid
                FROM thumbnails t
                JOIN thumbnails newer
                  ON t.obj_id = newer.obj_id
                 AND t.type = newer.type
                 AND t.survey IS NOT DISTINCT FROM newer.survey
                 AND (t.created_at, t.id) < (newer.created_at, newer.id)
                LIMIT {DELETE_BATCH_SIZE}
            )
            """
        )
        while conn.execute(delete_stmt).rowcount:
            pass

        conn.execute(
            sa.text(
                f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {CONSTRAINT_NAME} "
                "ON thumbnails (obj_id, type, survey)"
            )
        )

    # Metadata-only: attaches the concurrently-built index as the constraint's
    # backing index, so this doesn't rebuild/lock the table.
    op.execute(
        f"ALTER TABLE thumbnails ADD CONSTRAINT {CONSTRAINT_NAME} "
        f"UNIQUE USING INDEX {CONSTRAINT_NAME}"
    )


def downgrade():
    op.drop_constraint(CONSTRAINT_NAME, "thumbnails", type_="unique")
