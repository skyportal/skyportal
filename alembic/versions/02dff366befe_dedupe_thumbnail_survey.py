"""dedupe thumbnail survey

Revision ID: 02dff366befe
Revises: d4c17b9e5a02
Create Date: 2026-08-18

Backfills survey='ZTF' on legacy new/ref/sub thumbnails (added before the
survey column existed, when ZTF was the only broker source), drops the
resulting duplicate rows, and enforces one new/ref/sub thumbnail per
obj/survey going forward. See #6558-era "thumbnails are duplicated for ztf"
report: rows with survey=NULL and survey='ZTF' for the same obj/type were
being rendered as separate tiles by the source page.
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
        "UPDATE thumbnails SET survey = 'ZTF' "
        "WHERE survey IS NULL AND type IN ('new', 'ref', 'sub')"
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
