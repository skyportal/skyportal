"""add missing revisions

Revision ID: b74a9ff3b29d
Revises: c496222be5c6
Create Date: 2021-01-11 18:54:01.557106

"""

import sqlalchemy as sa
import sqlalchemy_utils

from alembic import op

# revision identifiers, used by Alembic.
revision = "b74a9ff3b29d"
down_revision = "c496222be5c6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("obj_id", sa.String(), nullable=False),
        sa.Column("list_name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["obj_id"], ["objs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_listings_list_name"), "listings", ["list_name"], unique=False
    )
    op.create_index(op.f("ix_listings_obj_id"), "listings", ["obj_id"], unique=False)
    op.create_index(op.f("ix_listings_user_id"), "listings", ["user_id"], unique=False)
    op.create_index(
        "listings_main_index",
        "listings",
        ["user_id", "obj_id", "list_name"],
        unique=True,
    )
    op.create_index(
        "listings_reverse_index",
        "listings",
        ["list_name", "obj_id", "user_id"],
        unique=True,
    )
    op.add_column(
        "allocations",
        sa.Column(
            "_altdata",
            sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("allocations", "_altdata")
    op.drop_index("listings_reverse_index", table_name="listings")
    op.drop_index("listings_main_index", table_name="listings")
    op.drop_index(op.f("ix_listings_user_id"), table_name="listings")
    op.drop_index(op.f("ix_listings_obj_id"), table_name="listings")
    op.drop_index(op.f("ix_listings_list_name"), table_name="listings")
    op.drop_table("listings")
