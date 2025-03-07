"""instrument field sequence

Revision ID: 486c860564a2
Revises: 3244123109f7
Create Date: 2022-03-10 18:29:48.866401

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "486c860564a2"
down_revision = "3244123109f7"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "instrumentfields",
        "field_id",
        existing_type=sa.INTEGER(),
        nullable=True,
        autoincrement=True,
    )
    op.execute('create sequence "public"."seq_field_id";')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "instrumentfields",
        "field_id",
        existing_type=sa.INTEGER(),
        nullable=False,
        autoincrement=True,
    )
    # ### end Alembic commands ###
