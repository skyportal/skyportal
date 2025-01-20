"""rename usernotification column to avoid collision with read permissions prop

Revision ID: 99958ac9a5b1
Revises: eb5ad7587e4e
Create Date: 2021-01-24 17:39:21.320389

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "99958ac9a5b1"
down_revision = "eb5ad7587e4e"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("usernotifications", "read", new_column_name="viewed")
    op.create_index(
        op.f("ix_usernotifications_viewed"),
        "usernotifications",
        ["viewed"],
        unique=False,
    )
    op.drop_index("ix_usernotifications_read", table_name="usernotifications")


def downgrade():
    op.alter_column("usernotifications", "viewed", new_column_name="read")
    op.create_index(
        "ix_usernotifications_read", "usernotifications", ["viewed"], unique=False
    )
    op.drop_index(op.f("ix_usernotifications_viewed"), table_name="usernotifications")
