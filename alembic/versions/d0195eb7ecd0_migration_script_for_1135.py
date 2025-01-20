"""migration script for 1135

Revision ID: d0195eb7ecd0
Revises: 93d1e086aafb
Create Date: 2020-10-23 11:06:37.665058

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d0195eb7ecd0"
down_revision = "93d1e086aafb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("photometry", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_photometry_owner_id"), "photometry", ["owner_id"], unique=False
    )

    # Data migration: takes a few steps...
    # Declare ORM table views. Note that the view contains old and new columns!
    photometry = sa.Table(
        "photometry",
        sa.MetaData(),
        sa.Column("id", sa.Integer()),
        sa.Column("owner_id", sa.Integer()),  # new column.
    )
    # Use Alchemy's connection and transaction to noodle over the data.
    connection = op.get_bind()
    # Set existing data to be owned by the provisioned admin.
    connection.execute(
        photometry.update().where(photometry.c.owner_id.is_(None)).values(owner_id=1)
    )

    op.create_foreign_key(
        None, "photometry", "users", ["owner_id"], ["id"], ondelete="CASCADE"
    )

    op.alter_column("photometry", "owner_id", nullable=False)
    op.add_column("spectra", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_spectra_owner_id"), "spectra", ["owner_id"], unique=False)

    spectra = sa.Table(
        "spectra",
        sa.MetaData(),
        sa.Column("id", sa.Integer()),
        sa.Column("owner_id", sa.Integer()),  # new column.
    )
    connection = op.get_bind()
    connection.execute(
        spectra.update().where(spectra.c.owner_id.is_(None)).values(owner_id=1)
    )

    op.alter_column("spectra", "owner_id", nullable=False)
    op.create_foreign_key(
        None, "spectra", "users", ["owner_id"], ["id"], ondelete="CASCADE"
    )


def downgrade():
    op.drop_constraint(None, "spectra", type_="foreignkey")
    op.drop_index(op.f("ix_spectra_owner_id"), table_name="spectra")
    op.drop_column("spectra", "owner_id")
    op.drop_constraint(None, "photometry", type_="foreignkey")
    op.drop_index(op.f("ix_photometry_owner_id"), table_name="photometry")
    op.drop_column("photometry", "owner_id")
