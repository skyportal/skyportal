"""refactor  permissions

Revision ID: eb5ad7587e4e
Revises: 5f2ba5579a79
Create Date: 2020-12-07 20:02:36.221787

"""

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

from alembic import op
from baselayer.app.models import JoinModel

# revision identifiers, used by Alembic.
revision = "eb5ad7587e4e"
down_revision = "5f2ba5579a79"
branch_labels = None
depends_on = None

# This migration adds an integer primary key to the join tables
mapped_classes = JoinModel.__subclasses__()


def upgrade():
    # add an integer primary key to the join tables this primary key is not
    # used anywhere as a foreign key so is safe to delete on schema downgrade
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    table_names = inspector.get_table_names()

    for cls in mapped_classes:
        table = cls.__tablename__
        if table in table_names:
            forward_ind_name = f"{table}_forward_ind"
            forward_index = getattr(cls, forward_ind_name)
            colpair = forward_index.columns.keys()
            op.execute(f'ALTER TABLE {table} DROP CONSTRAINT "{table}_pkey"')
            op.add_column(table, sa.Column("id", sa.Integer, primary_key=True))
            op.create_index(f"{table}_forward_ind", table, colpair, unique=True)


def downgrade():
    # restore a composite 2-column primary key to the join tables
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    table_names = inspector.get_table_names()

    for cls in mapped_classes:
        table = cls.__tablename__
        if table in table_names:
            forward_ind_name = f"{table}_forward_ind"
            forward_index = getattr(cls, forward_ind_name)
            colpair = forward_index.columns.keys()
            op.drop_index(f"{table}_forward_ind")
            op.drop_column(table, "id")
            op.create_primary_key(f"{table}_pkey", table, colpair)
