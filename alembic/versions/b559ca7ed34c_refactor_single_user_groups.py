"""refactor single user groups

Revision ID: b559ca7ed34c
Revises: 1300e24dcfe9
Create Date: 2020-10-30 16:44:31.577588

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b559ca7ed34c"
down_revision = "1300e24dcfe9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        op.f("ix_groups_single_user_group"),
        "groups",
        ["single_user_group"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_groups_single_user_group"), table_name="groups")
