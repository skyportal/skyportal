"""dedupe thumbnail survey

Revision ID: 02dff366befe
Revises: d4c17b9e5a02
Create Date: 2026-08-18

Backfills survey on legacy new/ref/sub thumbnails (added before the survey
column existed) whose object was later reprocessed under a known survey,
drops the resulting duplicate rows, and enforces one thumbnail per
obj/type/survey going forward. See "thumbnails are duplicated for ztf"
report: rows with survey=NULL and survey='ZTF' for the same obj/type were
being rendered as separate tiles by the source page.

The backfill only touches a NULL row when a sibling row for the same
obj/type already carries a real survey value (i.e. the object was
reprocessed post-migration) - that's the object's own observed survey, not
a guess. A NULL row with no such sibling is left alone: with only one row
for that obj/type it isn't rendered as a duplicate, and we don't know it
was ZTF (LSST/BOOM ingestion may predate this column too).

The dedup DELETE covers every type, not just new/ref/sub: the constraint
applies table-wide, and a POST accepts any ttype (e.g. new_gz), so a
duplicate on another type with a non-NULL survey would otherwise fail
``ADD CONSTRAINT`` and abort the migration. It runs batched and in
autocommit, and the unique index is built CONCURRENTLY, so this doesn't
hold a table-wide lock the way a single unbatched DELETE + non-concurrent
ADD CONSTRAINT would (see 3d9f7a1c2b45 for the same pattern on this table).
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "02dff366befe"
down_revision = "d4c17b9e5a02"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "thumbnails_obj_id_type_survey_key"
DELETE_BATCH_SIZE = 5000


def upgrade():
    op.execute(
        """
        UPDATE thumbnails t
        SET survey = t2.survey
        FROM thumbnails t2
        WHERE t.obj_id = t2.obj_id
          AND t.type = t2.type
          AND t.survey IS NULL
          AND t2.survey IS NOT NULL
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
