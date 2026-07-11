"""thumbnails (obj_id, type) covering index

Speeds the thumbnail_queue anti-join that finds objs missing a thumbnail type.

Revision ID: b3d9f21c7a4e
Revises: d7b2f4a1c9e0
Create Date: 2026-07-10 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b3d9f21c7a4e"
down_revision = "d7b2f4a1c9e0"
branch_labels = None
depends_on = None


def upgrade():
    # CONCURRENTLY so we don't lock the (large, hot) thumbnails table.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_thumbnails_obj_id_type "
            "ON thumbnails (obj_id, type)"
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_thumbnails_obj_id_type")
