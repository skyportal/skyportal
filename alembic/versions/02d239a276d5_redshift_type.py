"""Redshift type

Revision ID: 02d239a276d5
Revises: 3843619c7b1a
Create Date: 2026-11-18 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "02d239a276d5"
down_revision = "3843619c7b1a"
branch_labels = None
depends_on = None

redshift_type = sa.Enum("spectroscopic", "photometric", name="redshift_type")


def upgrade():
    redshift_type.create(op.get_bind(), checkfirst=True)
    op.add_column("objs", sa.Column("redshift_type", redshift_type, nullable=True))


def downgrade():
    op.drop_column("objs", "redshift_type")
    redshift_type.drop(op.get_bind(), checkfirst=True)
