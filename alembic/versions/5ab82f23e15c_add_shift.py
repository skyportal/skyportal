"""add shift

Revision ID: 5ab82f23e15c
Revises: 66ed6017e9ac
Create Date: 2022-02-01 05:24:23.927168

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5ab82f23e15c"
down_revision = "66ed6017e9ac"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_shifts_created_at"), "shifts", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_shifts_end_date"), "shifts", ["end_date"], unique=False)
    op.create_index(op.f("ix_shifts_group_id"), "shifts", ["group_id"], unique=False)
    op.create_index(
        op.f("ix_shifts_start_date"), "shifts", ["start_date"], unique=False
    )
    op.create_index(op.f("ix_shifts_name"), "shifts", ["name"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_shifts_start_date"), table_name="shifts")
    op.drop_index(op.f("ix_shifts_group_id"), table_name="shifts")
    op.drop_index(op.f("ix_shifts_end_date"), table_name="shifts")
    op.drop_index(op.f("ix_shifts_created_at"), table_name="shifts")
    op.drop_index(op.f("ix_shifts_name"), table_name="shifts")
    op.drop_table("shifts")
    # ### end Alembic commands ###
