"""Add teams and group_teams tables

Revision ID: 9bf2f46e850c
Revises: 52b02a40ac4d
Create Date: 2026-07-06 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9bf2f46e850c"
down_revision = "52b02a40ac4d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.String(), nullable=True),
        sa.Column("secondary_color", sa.String(), nullable=True),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("background_url", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_created_at"), "teams", ["created_at"], unique=False)
    op.create_index(op.f("ix_teams_name"), "teams", ["name"], unique=True)
    op.create_index(op.f("ix_teams_nickname"), "teams", ["nickname"], unique=True)

    op.create_table(
        "group_teams",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "group_teams_forward_ind",
        "group_teams",
        ["group_id", "team_id"],
        unique=True,
    )
    op.create_index(
        "group_teams_reverse_ind",
        "group_teams",
        ["team_id", "group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_group_teams_created_at"),
        "group_teams",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_group_teams_created_at"), table_name="group_teams")
    op.drop_index("group_teams_reverse_ind", table_name="group_teams")
    op.drop_index("group_teams_forward_ind", table_name="group_teams")
    op.drop_table("group_teams")
    op.drop_index(op.f("ix_teams_nickname"), table_name="teams")
    op.drop_index(op.f("ix_teams_name"), table_name="teams")
    op.drop_index(op.f("ix_teams_created_at"), table_name="teams")
    op.drop_table("teams")
