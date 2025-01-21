"""followup request bookkeeping

Revision ID: e1141138d4c6
Revises: 99822318096d
Create Date: 2020-10-29 17:09:34.590772

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e1141138d4c6"
down_revision = "99822318096d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "request_groups",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("followuprequest_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["followuprequest_id"], ["followuprequests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("followuprequest_id", "group_id"),
    )
    op.create_index(
        "request_groups_reverse_ind",
        "request_groups",
        ["group_id", "followuprequest_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("request_groups_reverse_ind", table_name="request_groups")
    op.drop_table("request_groups")
