"""Photometry/thumbnail index cleanup

Drops indexes that served zero reads in production (photometry
point/ref_flux/created_at/origin, group/stream_photometry created_at, objs
redshift/healpix/host_id, thumbnails created_at) and adds
ix_thumbnails_obj_id_type, which turns the thumbnail-service anti-join into an
index-only scan. Also replaces the unread surrogate-``id`` primary key on
group_photometry/stream_photometry with a composite (group_id/stream_id,
photometr_id) primary key, promoting the existing forward index.

Index adds/drops run CONCURRENTLY in an autocommit block (no table locks). The
PK restructure is metadata-only (the forward index is reused, no rebuild) so its
locks are brief.

NOTE: ix_thumbnails_obj_id is intentionally NOT dropped here — drop it in a
follow-up only after verifying (EXPLAIN) that plans use the new composite.

Revision ID: 3d9f7a1c2b45
Revises: d7b2f4a1c9e0
Create Date: 2026-07-04

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "3d9f7a1c2b45"
# NOTE: this branch had 3 alembic heads; set down_revision to the real single
# head after updating from latest main.
down_revision = "d7b2f4a1c9e0"
branch_labels = None
depends_on = None

# (index name, exact CREATE statement) captured from the live schema, used to
# recreate on downgrade.
DEAD_INDEXES = [
    (
        "ix_photometry_point",
        "CREATE INDEX ix_photometry_point ON photometry USING btree "
        '(((cosd(ra) * cosd("dec"))), ((sind(ra) * cosd("dec"))), sind("dec"))',
    ),
    (
        "ix_photometry_ref_flux",
        "CREATE INDEX ix_photometry_ref_flux ON photometry USING btree (ref_flux)",
    ),
    (
        "ix_photometry_created_at",
        "CREATE INDEX ix_photometry_created_at ON photometry USING btree (created_at)",
    ),
    (
        "ix_photometry_origin",
        "CREATE INDEX ix_photometry_origin ON photometry USING btree (origin)",
    ),
    (
        "ix_group_photometry_created_at",
        "CREATE INDEX ix_group_photometry_created_at ON group_photometry "
        "USING btree (created_at)",
    ),
    (
        "ix_stream_photometry_created_at",
        "CREATE INDEX ix_stream_photometry_created_at ON stream_photometry "
        "USING btree (created_at)",
    ),
    (
        "ix_objs_redshift",
        "CREATE INDEX ix_objs_redshift ON objs USING btree (redshift)",
    ),
    (
        "ix_objs_healpix",
        "CREATE INDEX ix_objs_healpix ON objs USING btree (healpix)",
    ),
    (
        "ix_objs_host_id",
        "CREATE INDEX ix_objs_host_id ON objs USING btree (host_id)",
    ),
    (
        "ix_thumbnails_created_at",
        "CREATE INDEX ix_thumbnails_created_at ON thumbnails USING btree (created_at)",
    ),
]

# (table, forward index name, composite columns)
JOIN_TABLES = [
    ("group_photometry", "group_photometry_forward_ind", "group_id, photometr_id"),
    ("stream_photometry", "stream_photometry_forward_ind", "stream_id, photometr_id"),
]


def upgrade():
    # Index adds/drops — CONCURRENTLY, outside a transaction.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_thumbnails_obj_id_type "
            "ON thumbnails (obj_id, type)"
        )
        for name, _create_sql in DEAD_INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")

    # Composite-PK restructure — metadata-only, transactional.
    for table, forward_ind, _cols in JOIN_TABLES:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {table}_pkey")
        op.execute(f"ALTER TABLE {table} DROP COLUMN id")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {table}_pkey "
            f"PRIMARY KEY USING INDEX {forward_ind}"
        )


def downgrade():
    # Reverse the PK restructure first (restore the surrogate id; rewrites table).
    for table, forward_ind, cols in JOIN_TABLES:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {table}_pkey")
        op.execute(f"CREATE UNIQUE INDEX {forward_ind} ON {table} ({cols})")
        op.execute(f"ALTER TABLE {table} ADD COLUMN id SERIAL PRIMARY KEY")

    # Recreate the dropped indexes; drop the composite.
    with op.get_context().autocommit_block():
        for _name, create_sql in DEAD_INDEXES:
            op.execute(
                create_sql.replace(
                    "CREATE INDEX ", "CREATE INDEX CONCURRENTLY IF NOT EXISTS ", 1
                )
            )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_thumbnails_obj_id_type")
