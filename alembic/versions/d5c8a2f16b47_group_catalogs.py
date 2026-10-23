"""Group-scoped read access for galaxy and spatial catalogs

Revision ID: d5c8a2f16b47
Revises: c4f1d2a9b7e3
Create Date: 2026-10-22 10:40:00.000000

"""

import sqlalchemy as sa

from alembic import op
from baselayer.app.env import load_env

# revision identifiers, used by Alembic.
revision = "d5c8a2f16b47"
down_revision = "c4f1d2a9b7e3"
branch_labels = None
depends_on = None

_, cfg = load_env()

# (join table, catalog table, join column)
JOINS = (
    ("group_galaxycatalogs", "galaxycatalogs", "galaxycatalog_id"),
    ("group_spatialcatalogs", "spatial_catalogs", "spatial_catalog_id"),
)


def upgrade():
    for table, catalogs, column in JOINS:
        op.create_table(
            table,
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("modified", sa.DateTime(), nullable=False),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("group_id", sa.Integer(), nullable=False),
            sa.Column(column, sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint([column], [f"{catalogs}.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            f"{table}_forward_ind", table, ["group_id", column], unique=True
        )
        op.create_index(
            f"{table}_reverse_ind", table, [column, "group_id"], unique=False
        )
        op.create_index(
            op.f(f"ix_{table}_created_at"), table, ["created_at"], unique=False
        )

    public_group_name = cfg["misc"]["public_group_name"]
    conn = op.get_bind()
    public_group_id = conn.execute(
        sa.text("SELECT id FROM groups WHERE name = :name"),
        {"name": public_group_name},
    ).scalar()

    for table, catalogs, column in JOINS:
        count = conn.execute(sa.text(f"SELECT count(*) FROM {catalogs}")).scalar()
        if not count:
            continue
        if public_group_id is None:
            raise RuntimeError(
                f"Cannot backfill catalog access: no group named "
                f"{public_group_name!r} (misc.public_group_name) exists, but "
                f"{count} row(s) are present in {catalogs}. Create that group, "
                f"or correct misc.public_group_name, before running this "
                f"migration."
            )
        op.execute(
            sa.text(
                f"""
                INSERT INTO {table} (created_at, modified, group_id, {column})
                SELECT now(), now(), :group_id, c.id
                FROM {catalogs} c
                ON CONFLICT DO NOTHING
                """
            ).bindparams(group_id=public_group_id)
        )


def downgrade():
    for table, _, _ in JOINS:
        op.drop_index(op.f(f"ix_{table}_created_at"), table_name=table)
        op.drop_index(f"{table}_reverse_ind", table_name=table)
        op.drop_index(f"{table}_forward_ind", table_name=table)
        op.drop_table(table)
