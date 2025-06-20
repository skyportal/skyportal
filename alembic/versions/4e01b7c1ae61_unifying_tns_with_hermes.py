"""Unifying TNS with hermes

Revision ID: 4e01b7c1ae61
Revises: 6f853af1e900
Create Date: 2025-06-19 17:24:20.538617

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "4e01b7c1ae61"
down_revision = "6f853af1e900"
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("tnsrobots", "external_publishing_bots")
    op.drop_index("ix_tnsrobots_created_at", table_name="tnsrobots")
    op.create_index(
        op.f("ix_external_publishing_bots_created_at"),
        "external_publishing_bots",
        ["created_at"],
        unique=False,
    )
    op.alter_column(
        "external_publishing_bots",
        "report_existing",
        new_column_name="publish_existing_tns_objects",
        existing_type=sa.Boolean(),
    )
    op.alter_column(
        "external_publishing_bots",
        "bot_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "external_publishing_bots",
        "source_group_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "external_publishing_bots",
        "_altdata",
        new_column_name="_tns_altdata",
        existing_type=postgresql.BYTEA(),
    )
    op.add_column(
        "external_publishing_bots",
        sa.Column(
            "enable_publish_to_hermes",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "external_publishing_bots",
        sa.Column(
            "enable_publish_to_tns",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    # op.drop_constraint('tnsrobot_group_users_tnsrobot_group_id_fkey', 'external_publishing_bot_group_users',
    #                    type_='foreignkey')
    # sa.ForeignKeyConstraint(
    #     ["instrument_id"], ["instruments.id"], ondelete="CASCADE"
    # ),

    ##########
    op.rename_table("tnsrobot_coauthors", "external_publishing_bot_coauthors")
    op.alter_column(
        "external_publishing_bot_coauthors",
        "tnsrobot_id",
        new_column_name="external_publishing_bot_id",
        existing_type=sa.Integer(),
    )

    ##########
    op.rename_table("tnsrobot_groups", "external_publishing_bot_groups")
    op.alter_column(
        "external_publishing_bot_groups",
        "tnsrobot_id",
        new_column_name="external_publishing_bot_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "external_publishing_bot_groups",
        "auto_report",
        new_column_name="auto_publish_to_tns",
        existing_type=sa.Boolean(),
        existing_server_default=sa.text("false"),
    )
    op.alter_column(
        "external_publishing_bot_groups",
        "auto_report_allow_bots",
        new_column_name="auto_publish_allow_bots",
        existing_type=sa.Boolean(),
        existing_server_default=sa.text("false"),
    )
    op.add_column(
        "external_publishing_bot_groups",
        sa.Column(
            "auto_publish_to_hermes",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.drop_constraint(
        "tnsrobot_groups_tnsrobot_id_fkey",
        "external_publishing_bot_groups",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_groups_group_id_fkey",
        "external_publishing_bot_groups",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "bot_groups_bot_id_fkey",
        "external_publishing_bot_groups",
        "external_publishing_bots",
        ["external_publishing_bot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "bot_groups_group_id_fkey",
        "external_publishing_bot_groups",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )

    ##########
    op.rename_table("tnsrobot_group_users", "external_publishing_bot_group_users")
    op.alter_column(
        "external_publishing_bot_group_users",
        "tnsrobot_group_id",
        new_column_name="external_publishing_bot_group_id",
        existing_type=sa.Integer(),
    )
    op.drop_constraint(
        "tnsrobot_group_users_tnsrobot_group_id_fkey",
        "external_publishing_bot_group_users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_group_users_group_user_id_fkey",
        "external_publishing_bot_group_users",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "bot_group_users_bot_group_id_fkey",
        "external_publishing_bot_group_users",
        "external_publishing_bot_groups",
        ["external_publishing_bot_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "bot_group_users_group_user_id_fkey",
        "external_publishing_bot_group_users",
        "group_users",
        ["group_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    ##########
    op.rename_table("tnsrobot_submissions", "external_publishing_submissions")
    op.alter_column(
        "external_publishing_submissions",
        "tnsrobot_id",
        new_column_name="external_publishing_bot_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "external_publishing_submissions",
        "custom_reporting_string",
        new_column_name="custom_publishing_string",
        existing_type=sa.String(),
        existing_nullable=True,
    )
    op.alter_column(
        "external_publishing_submissions",
        "status",
        new_column_name="tns_status",
        existing_type=sa.String(),
        existing_nullable=True,
        existing_server_default=None,
        nullable=True,
    )
    op.alter_column(
        "external_publishing_submissions",
        "submission_id",
        new_column_name="tns_submission_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
        existing_server_default=None,
        nullable=True,
    )
    op.alter_column(
        "external_publishing_submissions",
        "payload",
        new_column_name="tns_payload",
        existing_type=postgresql.JSONB(),
        existing_nullable=True,
    )
    op.alter_column(
        "external_publishing_submissions",
        "response",
        new_column_name="tns_response",
        existing_type=postgresql.JSONB(),
        existing_nullable=True,
    )
    op.add_column(
        "external_publishing_submissions",
        sa.Column(
            "publish_to_tns",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "external_publishing_submissions",
        sa.Column(
            "publish_to_hermes",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "external_publishing_submissions",
        sa.Column("hermes_status", sa.String(), nullable=True),
    )
    op.add_column(
        "external_publishing_submissions",
        sa.Column(
            "hermes_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade():
    op.drop_column("external_publishing_submissions", "publish_to_tns")
    op.drop_column("external_publishing_submissions", "publish_to_hermes")
    op.drop_column("external_publishing_submissions", "hermes_status")
    op.drop_column("external_publishing_submissions", "hermes_response")

    op.alter_column(
        "external_publishing_submissions",
        "tns_response",
        new_column_name="response",
        existing_type=postgresql.JSONB(),
        existing_nullable=True,
    )
    op.alter_column(
        "external_publishing_submissions",
        "tns_payload",
        new_column_name="payload",
        existing_type=postgresql.JSONB(),
        existing_nullable=True,
    )
    op.alter_column(
        "external_publishing_submissions",
        "tns_submission_id",
        new_column_name="submission_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "external_publishing_submissions",
        "tns_status",
        new_column_name="status",
        existing_type=sa.String(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "external_publishing_submissions",
        "custom_publishing_string",
        new_column_name="custom_reporting_string",
        existing_type=sa.String(),
        existing_nullable=True,
    )
    op.alter_column(
        "external_publishing_submissions",
        "external_publishing_bot_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.rename_table("external_publishing_submissions", "tnsrobot_submissions")

    ##########
    op.drop_constraint(
        "bot_group_users_bot_group_id_fkey",
        "external_publishing_bot_group_users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "bot_group_users_group_user_id_fkey",
        "external_publishing_bot_group_users",
        type_="foreignkey",
    )

    op.alter_column(
        "external_publishing_bot_group_users",
        "external_publishing_bot_group_id",
        new_column_name="tnsrobot_group_id",
        existing_type=sa.Integer(),
    )
    op.rename_table("external_publishing_bot_group_users", "tnsrobot_group_users")

    op.create_foreign_key(
        "tnsrobot_group_users_tnsrobot_group_id_fkey",
        "tnsrobot_group_users",
        "tnsrobot_groups",
        ["tnsrobot_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "tnsrobot_group_users_group_user_id_fkey",
        "tnsrobot_group_users",
        "group_users",
        ["group_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    ##########
    op.drop_constraint(
        "bot_groups_bot_id_fkey", "external_publishing_bot_groups", type_="foreignkey"
    )
    op.drop_constraint(
        "bot_groups_group_id_fkey", "external_publishing_bot_groups", type_="foreignkey"
    )

    op.drop_column("external_publishing_bot_groups", "auto_publish_to_hermes")
    op.alter_column(
        "external_publishing_bot_groups",
        "auto_publish_to_tns",
        new_column_name="auto_report",
        existing_type=sa.Boolean(),
    )
    op.alter_column(
        "external_publishing_bot_groups",
        "auto_publish_allow_bots",
        new_column_name="auto_report_allow_bots",
        existing_type=sa.Boolean(),
    )
    op.alter_column(
        "external_publishing_bot_groups",
        "external_publishing_bot_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )
    op.rename_table("external_publishing_bot_groups", "tnsrobot_groups")

    op.create_foreign_key(
        "tnsrobot_groups_tnsrobot_id_fkey",
        "tnsrobot_groups",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "tnsrobot_groups_group_id_fkey",
        "tnsrobot_groups",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )

    ##########
    op.alter_column(
        "external_publishing_bot_coauthors",
        "external_publishing_bot_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )
    op.rename_table("external_publishing_bot_coauthors", "tnsrobot_coauthors")

    ##########
    op.drop_column("external_publishing_bots", "enable_publish_to_hermes")
    op.drop_column("external_publishing_bots", "enable_publish_to_tns")
    op.alter_column(
        "external_publishing_bots",
        "_tns_altdata",
        new_column_name="_altdata",
        existing_type=postgresql.BYTEA(),
    )
    op.alter_column(
        "external_publishing_bots",
        "source_group_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "external_publishing_bots",
        "bot_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "external_publishing_bots",
        "publish_existing_tns_objects",
        new_column_name="report_existing",
        existing_type=sa.Boolean(),
    )
    op.drop_index(
        op.f("ix_external_publishing_bots_created_at"),
        table_name="external_publishing_bots",
    )
    op.create_index(
        "ix_tnsrobots_created_at",
        "external_publishing_bots",
        ["created_at"],
        unique=False,
    )
    op.rename_table("external_publishing_bots", "tnsrobots")
