"""dedupe thumbnail survey

Revision ID: 02dff366befe
Revises: d4c17b9e5a02
Create Date: 2026-08-18

Backfills survey on legacy new/ref/sub thumbnails (added before the survey
column existed) whose object was later reprocessed under a known survey,
drops the resulting duplicate rows, and enforces one new/ref/sub thumbnail
per obj/survey going forward. See "thumbnails are duplicated for ztf"
report: rows with survey=NULL and survey='ZTF' for the same obj/type were
being rendered as separate tiles by the source page.

The backfill only touches a NULL row when a sibling row for the same
obj/type already carries a real survey value (i.e. the object was
reprocessed post-migration) - that's the object's own observed survey, not
a guess. A NULL row with no such sibling is left alone: with only one row
for that obj/type it isn't rendered as a duplicate, and we don't know it
was ZTF (LSST/BOOM ingestion may predate this column too).
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "02dff366befe"
down_revision = "d4c17b9e5a02"
branch_labels = None
depends_on = None


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
    # Keep the most recent row per (obj_id, type, survey); the shared file on
    # disk (path is keyed on obj_id/type only) is untouched by this raw delete.
    op.execute(
        """
        DELETE FROM thumbnails t
        USING thumbnails newer
        WHERE t.obj_id = newer.obj_id
          AND t.type = newer.type
          AND t.survey IS NOT DISTINCT FROM newer.survey
          AND t.type IN ('new', 'ref', 'sub')
          AND (t.created_at, t.id) < (newer.created_at, newer.id)
        """
    )
    op.create_unique_constraint(
        "thumbnails_obj_id_type_survey_key", "thumbnails", ["obj_id", "type", "survey"]
    )


def downgrade():
    op.drop_constraint(
        "thumbnails_obj_id_type_survey_key", "thumbnails", type_="unique"
    )
