"""photometry bigint id

Widen photometry.id, its sequence, and the four inbound FK columns from int4
to bigint to avoid sequence overflow.

Revision ID: 52b02a40ac4d
Revises: 363f77c7a441
Create Date: 2026-07-14

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "52b02a40ac4d"
down_revision = "363f77c7a441"
branch_labels = None
depends_on = None

# (table, column) pairs for the inbound FKs referencing photometry.id.
FK_COLUMNS = [
    ("annotations_on_photometry", "photometry_id"),
    ("photometryvalidations", "photometry_id"),
    ("group_photometry", "photometr_id"),
    ("stream_photometry", "photometr_id"),
]


def upgrade():
    op.execute("ALTER SEQUENCE photometry_id_seq AS bigint")
    op.alter_column(
        "photometry",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        autoincrement=True,
    )
    for table, column in FK_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )


def downgrade():
    for table, column in FK_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
    op.alter_column(
        "photometry",
        "id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        autoincrement=True,
    )
    op.execute("ALTER SEQUENCE photometry_id_seq AS integer")
