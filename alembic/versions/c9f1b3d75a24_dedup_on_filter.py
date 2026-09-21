"""Deduplicate photometry on the filter as well

Two bands measured at one epoch are two measurements, but the dedup index did
not carry the filter. Same-epoch upper limits of equal depth in different bands
therefore shared a key -- flux is NaN for both, and a btree treats NaN as equal
to NaN -- so a single upsert carrying both was rejected with

    ON CONFLICT DO UPDATE command cannot affect row a second time

and every row in that statement was lost.

Widening a unique index only ever loosens it, so no stored row can conflict
with the new one. The new index is built CONCURRENTLY under a temporary name
and renamed over the old, which keeps a unique index in place throughout
rather than leaving a window with none.

Revision ID: c9f1b3d75a24
Revises: b7e4c1a90f33
Create Date: 2026-09-19

"""

import sqlalchemy as sa

from alembic import op

revision = "c9f1b3d75a24"
down_revision = "b7e4c1a90f33"
branch_labels = None
depends_on = None

NAME = "deduplication_index"
BUILDING = "deduplication_index_building"

# The band sits after mjd so that (obj_id, instrument_id, origin, mjd) stays a
# usable prefix for find_duplicate_photometry's lookup.
WITH_FILTER = '(obj_id, instrument_id, origin, mjd, "filter", fluxerr, flux)'
WITHOUT_FILTER = "(obj_id, instrument_id, origin, mjd, fluxerr, flux)"


def _drop_if_invalid(conn, name):
    """A failed CONCURRENTLY build leaves an invalid index IF NOT EXISTS reuses."""
    if conn.execute(
        sa.text(
            "SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
            "WHERE c.relname = :name AND NOT i.indisvalid"
        ),
        {"name": name},
    ).scalar():
        conn.execute(sa.text(f"DROP INDEX CONCURRENTLY {name}"))


def _swap(conn, columns):
    _drop_if_invalid(conn, BUILDING)
    conn.execute(
        sa.text(
            f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {BUILDING} "
            f"ON photometry USING btree {columns}"
        )
    )
    conn.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {NAME}"))
    conn.execute(sa.text(f"ALTER INDEX {BUILDING} RENAME TO {NAME}"))


def upgrade():
    conn = op.get_bind()
    with op.get_context().autocommit_block():
        _swap(conn, WITH_FILTER)


def downgrade():
    # Rows that differ only by filter are legal under the wider index and not
    # under the narrower one, so this fails where any now exist. That is the
    # data refusing to fit, not a fault in the migration.
    conn = op.get_bind()
    with op.get_context().autocommit_block():
        _swap(conn, WITHOUT_FILTER)
