"""Add PrimaryKey constraint to JoinModel.id

Revision ID: 5365c004a923
Revises: 2ed67629cdb3
Create Date: 2021-02-22 12:46:46.137261

"""

from sqlalchemy.engine.reflection import Inspector

from alembic import op
from baselayer.app.models import JoinModel

# revision identifiers, used by Alembic.
revision = "5365c004a923"
down_revision = "2ed67629cdb3"
branch_labels = None
depends_on = None


mapped_classes = JoinModel.__subclasses__()


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    table_names = inspector.get_table_names()

    op.create_primary_key("candidates_pkey", "candidates", ["id"])
    for cls in mapped_classes:
        table = cls.__tablename__
        if table in table_names:
            op.create_primary_key(f"{table}_pkey", table, ["id"])


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    table_names = inspector.get_table_names()

    op.drop_constraint("candidates_pkey", "candidates")
    for cls in mapped_classes:
        table = cls.__tablename__
        if table in table_names:
            op.drop_constraint(f"{table}_pkey", table)
