"""adding objtag models

Revision ID: 6f853af1e900
Revises: 5f949cc5cae9
Create Date: 2025-05-06 20:21:58.420749

"""

import sqlalchemy as sa
import sqlalchemy_utils

from alembic import op

# revision identifiers, used by Alembic.
revision = "6f853af1e900"
down_revision = "5f949cc5cae9"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "objtagoptions",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_objtagoptions_created_at"),
        "objtagoptions",
        ["created_at"],
        unique=False,
    )
    op.create_table(
        "obj_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("obj_id", sa.String(), nullable=False),
        sa.Column("objtagoption_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["obj_id"], ["objs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["objtagoption_id"], ["objtagoptions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_obj_tags_created_at"), "obj_tags", ["created_at"], unique=False
    )
    op.create_index(
        "obj_tags_forward_ind", "obj_tags", ["obj_id", "objtagoption_id"], unique=True
    )
    op.create_index(
        "obj_tags_reverse_ind", "obj_tags", ["objtagoption_id", "obj_id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("obj_tags_reverse_ind", table_name="obj_tags")
    op.drop_index("obj_tags_forward_ind", table_name="obj_tags")
    op.drop_index(op.f("ix_obj_tags_created_at"), table_name="obj_tags")
    op.drop_table("obj_tags")
    op.drop_index(op.f("ix_objtagoptions_created_at"), table_name="objtagoptions")
    op.drop_table("objtagoptions")
    # ### end Alembic commands ###
