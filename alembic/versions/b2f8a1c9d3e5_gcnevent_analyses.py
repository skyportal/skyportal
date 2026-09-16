"""gcnevent_analyses tables

Revision ID: b2f8a1c9d3e5
Revises: a1c7e4f93b52
Create Date: 2026-09-16 09:30:00.000000

"""

import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "b2f8a1c9d3e5"
down_revision = "a1c7e4f93b52"
branch_labels = None
depends_on = None

# Reuse the enum created with obj_analyses; do not re-create it.
webhookstatus = postgresql.ENUM(
    "queued",
    "pending",
    "completed",
    "failure",
    "cancelled",
    "timed_out",
    name="webhookstatustypes",
    create_type=False,
)


def upgrade():
    op.create_table(
        "gcnevent_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("invalid_after", sa.DateTime(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("handled_by_url", sa.String(), nullable=False),
        sa.Column("status", webhookstatus, nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("last_activity", sa.DateTime(), nullable=True),
        sa.Column("status_message", sa.String(), nullable=True),
        sa.Column("_unique_id", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=True),
        sa.Column("_full_name", sa.String(), nullable=True),
        sa.Column("show_parameters", sa.Boolean(), nullable=False),
        sa.Column("show_plots", sa.Boolean(), nullable=False),
        sa.Column("show_corner", sa.Boolean(), nullable=False),
        sa.Column(
            "analysis_parameters",
            sqlalchemy_utils.types.json.JSONType(),
            nullable=True,
        ),
        sa.Column(
            "input_filters",
            sqlalchemy_utils.types.json.JSONType(),
            nullable=True,
        ),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("analysis_service_id", sa.Integer(), nullable=False),
        sa.Column("dateobs", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_service_id"], ["analysis_services.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dateobs"], ["gcnevents.dateobs"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("_unique_id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_gcnevent_analyses_analysis_service_id"),
        "gcnevent_analyses",
        ["analysis_service_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gcnevent_analyses_author_id"),
        "gcnevent_analyses",
        ["author_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gcnevent_analyses_created_at"),
        "gcnevent_analyses",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gcnevent_analyses_dateobs"),
        "gcnevent_analyses",
        ["dateobs"],
        unique=False,
    )

    op.create_table(
        "group_gcnevent_analyses",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("gcnevent_analyse_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["gcnevent_analyse_id"], ["gcnevent_analyses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "group_gcnevent_analyses_forward_ind",
        "group_gcnevent_analyses",
        ["group_id", "gcnevent_analyse_id"],
        unique=True,
    )
    op.create_index(
        "group_gcnevent_analyses_reverse_ind",
        "group_gcnevent_analyses",
        ["gcnevent_analyse_id", "group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_group_gcnevent_analyses_created_at"),
        "group_gcnevent_analyses",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_table("group_gcnevent_analyses")
    op.drop_table("gcnevent_analyses")
