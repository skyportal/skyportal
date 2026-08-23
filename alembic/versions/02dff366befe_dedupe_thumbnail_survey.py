"""dedupe thumbnail survey

Revision ID: 02dff366befe
Revises: a3d81c4f7b26
Create Date: 2026-08-18

Uppercases existing survey values, backfills survey on legacy new/ref/sub rows
from their most recent same-obj/type sibling (a NULL row with no such sibling is
left alone), dedupes any remaining (obj_id, type, survey) duplicates table-wide,
and adds a unique constraint to enforce one thumbnail per survey going forward.
Batched per obj_id page + CONCURRENTLY index build to avoid a table-wide lock
(see 3d9f7a1c2b45 for the same pattern). Fixes duplicate ZTF tiles on the source
page. Surviving rows keep their pre-survey file_uri, so two surveys can still
share one file on disk until the next ingest rewrites them to the suffixed name.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "02dff366befe"
down_revision = "a3d81c4f7b26"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "thumbnails_obj_id_type_survey_key"
OBJ_BATCH_SIZE = 5000

# Page over obj_id: a bare LIMIT rescans from the top each round, so the pass
# would grow quadratically in the number of batches.
NEXT_PAGE = sa.text(
    """
    SELECT max(obj_id) FROM (
        SELECT DISTINCT obj_id
        FROM thumbnails
        WHERE obj_id > :lo
        ORDER BY obj_id
        LIMIT :n
    ) page
    """
)

# Must run before the dedupe: "Ztf" and "ZTF" are distinct under the constraint.
UPPERCASE = sa.text(
    """
    UPDATE thumbnails
    SET survey = upper(trim(survey))
    WHERE obj_id > :lo AND obj_id <= :hi
      AND survey IS NOT NULL
      AND survey <> upper(trim(survey))
    """
)

# DISTINCT ON picks one deterministic sibling (the most recent) per obj_id/type:
# a plain self-join here left the choice up to Postgres when an obj/type had
# siblings on two different surveys.
BACKFILL = sa.text(
    """
    UPDATE thumbnails t
    SET survey = pick.survey
    FROM (
        SELECT DISTINCT ON (obj_id, type) obj_id, type, survey
        FROM thumbnails
        WHERE obj_id > :lo AND obj_id <= :hi AND survey IS NOT NULL
        ORDER BY obj_id, type, created_at DESC, id DESC
    ) pick
    WHERE t.obj_id > :lo AND t.obj_id <= :hi
      AND t.obj_id = pick.obj_id
      AND t.type = pick.type
      AND t.survey IS NULL
      AND t.type IN ('new', 'ref', 'sub')
    """
)

# Keep the most recent row per (obj_id, type, survey). The file on disk is left
# alone by this raw delete, which is what lets duplicates still sharing one
# pre-survey filename go away without breaking the surviving row.
DEDUPE = sa.text(
    """
    DELETE FROM thumbnails t
    USING thumbnails newer
    WHERE t.obj_id > :lo AND t.obj_id <= :hi
      AND t.obj_id = newer.obj_id
      AND t.type = newer.type
      AND t.survey IS NOT DISTINCT FROM newer.survey
      AND (t.created_at, t.id) < (newer.created_at, newer.id)
    """
)


def upgrade():
    conn = op.get_bind()
    with op.get_context().autocommit_block():
        # A failed CONCURRENTLY build leaves an invalid index that IF NOT EXISTS
        # would reuse and the final ALTER would reject.
        if conn.execute(
            sa.text(
                "SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
                "WHERE c.relname = :name AND NOT i.indisvalid"
            ),
            {"name": CONSTRAINT_NAME},
        ).scalar():
            conn.execute(sa.text(f"DROP INDEX CONCURRENTLY {CONSTRAINT_NAME}"))

        lo = ""
        while True:
            hi = conn.execute(NEXT_PAGE, {"lo": lo, "n": OBJ_BATCH_SIZE}).scalar()
            if hi is None:
                break
            page = {"lo": lo, "hi": hi}
            conn.execute(UPPERCASE, page)
            conn.execute(BACKFILL, page)
            conn.execute(DEDUPE, page)
            lo = hi

        conn.execute(
            sa.text(
                f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {CONSTRAINT_NAME} "
                "ON thumbnails (obj_id, type, survey)"
            )
        )

    # Metadata-only: attaches the concurrently-built index as the constraint's
    # backing index, so this doesn't rebuild the table.
    op.execute(
        f"ALTER TABLE thumbnails ADD CONSTRAINT {CONSTRAINT_NAME} "
        f"UNIQUE USING INDEX {CONSTRAINT_NAME}"
    )


def downgrade():
    op.drop_constraint(CONSTRAINT_NAME, "thumbnails", type_="unique")
