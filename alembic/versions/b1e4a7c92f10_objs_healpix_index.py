"""Index objs.healpix

Localization and cone searches restrict objs by healpix range, and
`cone_healpix_prefilter` is written for an indexed column, but no index existed:
both fell back to a sequential scan over every object. On a 1.3M row table the
localization range join went from 51s to 0.02s with this in place.

Built CONCURRENTLY so ingestion keeps writing during the build.

Revision ID: b1e4a7c92f10
Revises: c7a2e8b41d63
Create Date: 2026-09-04

"""

import sqlalchemy as sa

from alembic import op

revision = "b1e4a7c92f10"
down_revision = "c7a2e8b41d63"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_objs_healpix"


def upgrade():
    conn = op.get_bind()
    with op.get_context().autocommit_block():
        # A failed CONCURRENTLY build leaves an invalid index that IF NOT EXISTS
        # would reuse.
        if conn.execute(
            sa.text(
                "SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
                "WHERE c.relname = :name AND NOT i.indisvalid"
            ),
            {"name": INDEX_NAME},
        ).scalar():
            conn.execute(sa.text(f"DROP INDEX CONCURRENTLY {INDEX_NAME}"))
        conn.execute(
            sa.text(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME} "
                "ON objs USING btree (healpix)"
            )
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.get_bind().execute(
            sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}")
        )
