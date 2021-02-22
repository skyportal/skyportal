"""Add PrimaryKey constraint to JoinModel.id

Revision ID: 5365c004a923
Revises: 1c2d593e9778
Create Date: 2021-02-22 12:46:46.137261

"""
from alembic import op
from baselayer.app.models import JoinModel


# revision identifiers, used by Alembic.
revision = '5365c004a923'
down_revision = '1c2d593e9778'
branch_labels = None
depends_on = None


mapped_classes = JoinModel.__subclasses__()


def upgrade():
    op.create_primary_key("candidates_pkey", "candidates", ["id"])
    for cls in mapped_classes:
        table = cls.__tablename__
        op.create_primary_key(f"{table}_pkey", table, ["id"])


def downgrade():
    op.drop_constraint("candidates_pkey", "candidates")
    for cls in mapped_classes:
        table = cls.__tablename__
        op.drop_constraint(f"{table}_pkey", table)
