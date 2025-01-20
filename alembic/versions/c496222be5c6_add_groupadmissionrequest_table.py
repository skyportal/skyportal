"""Add GroupAdmissionRequest table

Revision ID: c496222be5c6
Revises: 2a17ca9d5438
Create Date: 2020-12-08 16:16:08.064946

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c496222be5c6"
down_revision = "2a17ca9d5438"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "groupadmissionrequests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "accepted", "declined", name="admission_request_status"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_groupadmissionrequests_group_id"),
        "groupadmissionrequests",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_groupadmissionrequests_user_id"),
        "groupadmissionrequests",
        ["user_id"],
        unique=False,
    )
    op.add_column("groups", sa.Column("private", sa.Boolean()))
    op.create_index(op.f("ix_groups_private"), "groups", ["private"], unique=False)
    groups = sa.Table(
        "groups",
        sa.MetaData(),
        sa.Column("id", sa.Integer()),
        sa.Column("private", sa.Boolean()),
    )
    conn = op.get_bind()
    conn.execute(
        groups.update().where(groups.c.private.is_(None)).values(private=False)
    )
    op.alter_column("groups", "private", nullable=False)


def downgrade():
    op.drop_index(op.f("ix_groups_private"), table_name="groups")
    op.drop_column("groups", "private")
    op.drop_index(
        op.f("ix_groupadmissionrequests_user_id"), table_name="groupadmissionrequests"
    )
    op.drop_index(
        op.f("ix_groupadmissionrequests_group_id"), table_name="groupadmissionrequests"
    )
    op.drop_table("groupadmissionrequests")
    op.execute("DROP TYPE admission_request_status")
