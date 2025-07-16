"""Unifying TNS with hermes

Revision ID: 4e01b7c1ae61
Revises: c3ee8a0c8d51
Create Date: 2025-06-19 17:24:20.538617

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "4e01b7c1ae61"
down_revision = "c3ee8a0c8d51"
branch_labels = None
depends_on = None

tables_to_rename = [
    ("tnsrobots", "sharingservices"),
    ("instrument_tnsrobots", "instrument_sharingservices"),
    ("stream_tnsrobots", "stream_sharingservices"),
    ("tnsrobot_coauthors", "sharingservices_coauthors"),
    ("tnsrobot_groups", "sharingservices_groups"),
    ("tnsrobot_group_users", "sharingservices_group_users"),
    ("tnsrobot_submissions", "sharingservices_submissions"),
]


def upgrade():
    # Drop foreign key constraints
    op.drop_constraint(
        "tnsrobot_submissions_obj_id_fkey",
        "tnsrobot_submissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_submissions_user_id_fkey",
        "tnsrobot_submissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_submissions_tnsrobot_id_fkey",
        "tnsrobot_submissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_group_users_group_user_id_fkey",
        "tnsrobot_group_users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_group_users_tnsrobot_group_id_fkey",
        "tnsrobot_group_users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_groups_group_id_fkey",
        "tnsrobot_groups",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_groups_tnsrobot_id_fkey",
        "tnsrobot_groups",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_coauthors_user_id_fkey",
        "tnsrobot_coauthors",
        type_="foreignkey",
    )
    op.drop_constraint(
        "tnsrobot_coauthors_tnsrobot_id_fkey",
        "tnsrobot_coauthors",
        type_="foreignkey",
    )
    op.drop_constraint(
        "stream_tnsrobots_stream_id_fkey",
        "stream_tnsrobots",
        type_="foreignkey",
    )
    op.drop_constraint(
        "stream_tnsrobots_tnsrobot_id_fkey",
        "stream_tnsrobots",
        type_="foreignkey",
    )
    op.drop_constraint(
        "instrument_tnsrobots_instrument_id_fkey",
        "instrument_tnsrobots",
        type_="foreignkey",
    )
    op.drop_constraint(
        "instrument_tnsrobots_tnsrobot_id_fkey",
        "instrument_tnsrobots",
        type_="foreignkey",
    )

    # sharing_service_bots
    op.add_column(
        "tnsrobots",
        sa.Column(
            "enable_sharing_with_hermes",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "tnsrobots",
        sa.Column(
            "enable_sharing_with_tns",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.alter_column(
        "tnsrobots",
        "report_existing",
        new_column_name="publish_existing_tns_objects",
        nullable=True,
        existing_type=sa.Boolean(),
    )
    op.alter_column("tnsrobots", "bot_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column(
        "tnsrobots", "source_group_id", existing_type=sa.Integer(), nullable=True
    )
    op.alter_column(
        "tnsrobots",
        "_altdata",
        new_column_name="_tns_altdata",
        existing_type=postgresql.BYTEA(),
    )

    # instrument_sharing_service_bots
    op.alter_column(
        "instrument_tnsrobots",
        "tnsrobot_id",
        new_column_name="sharingservice_id",
        existing_type=sa.Integer(),
    )

    # stream_sharing_service_bots
    op.alter_column(
        "stream_tnsrobots",
        "tnsrobot_id",
        new_column_name="sharingservice_id",
        existing_type=sa.Integer(),
    )

    # sharing_service_coauthors
    op.alter_column(
        "tnsrobot_coauthors",
        "tnsrobot_id",
        new_column_name="sharingservice_id",
        existing_type=sa.Integer(),
    )

    # sharing_service_groups
    op.alter_column(
        "tnsrobot_groups",
        "tnsrobot_id",
        new_column_name="sharingservice_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "tnsrobot_groups",
        "auto_report",
        new_column_name="auto_share_to_tns",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )
    op.alter_column(
        "tnsrobot_groups",
        "auto_report_allow_bots",
        new_column_name="auto_sharing_allow_bots",
        existing_type=sa.Boolean(),
    )
    op.add_column(
        "tnsrobot_groups",
        sa.Column(
            "auto_share_to_hermes",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # sharing_service_group_users
    op.alter_column(
        "tnsrobot_group_users",
        "tnsrobot_group_id",
        new_column_name="sharing_service_group_id",
        existing_type=sa.Integer(),
    )

    # sharing_service_submissions
    op.alter_column(
        "tnsrobot_submissions",
        "tnsrobot_id",
        new_column_name="sharingservice_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "tnsrobot_submissions",
        "custom_reporting_string",
        new_column_name="custom_publishing_string",
        existing_type=sa.String(),
    )
    op.alter_column(
        "tnsrobot_submissions",
        "status",
        new_column_name="tns_status",
        existing_type=sa.String(),
        nullable=True,
    )
    op.alter_column(
        "tnsrobot_submissions",
        "submission_id",
        new_column_name="tns_submission_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "tnsrobot_submissions",
        "payload",
        new_column_name="tns_payload",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "tnsrobot_submissions",
        "response",
        new_column_name="tns_response",
        existing_type=postgresql.JSONB(),
    )
    op.add_column(
        "tnsrobot_submissions",
        sa.Column(
            "publish_to_tns",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "tnsrobot_submissions",
        sa.Column(
            "publish_to_hermes",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("tnsrobot_submissions", sa.Column("hermes_status", sa.String()))
    op.add_column(
        "tnsrobot_submissions", sa.Column("hermes_response", postgresql.JSONB())
    )

    for old, new in tables_to_rename:
        # Rename tables
        op.rename_table(old, new)

        # Manage index
        op.drop_index(f"ix_{old}_created_at", table_name=new)
        op.create_index(
            f"ix_{new}_created_at",
            new,
            ["created_at"],
            unique=False,
        )
        if "instrument" in new or "stream" in new:
            op.drop_index(f"{old}_reverse_ind", table_name=new)
            op.drop_index(f"{old}_forward_ind", table_name=new)
            op.create_index(
                f"{new}_reverse_ind",
                new,
                [
                    "sharingservice_id",
                    f"{'instrument' if 'instrument' in new else 'stream'}_id",
                ],
                unique=False,
            )
            op.create_index(
                f"{new}_forward_ind",
                new,
                [
                    f"{'instrument' if 'instrument' in new else 'stream'}_id",
                    "sharingservice_id",
                ],
                unique=True,
            )

        op.execute(f"ALTER SEQUENCE {old}_id_seq RENAME TO {new}_id_seq")
        op.execute(f"ALTER SEQUENCE {new}_id_seq OWNED BY {new}.id")
        op.alter_column(
            new,
            "id",
            server_default=sa.text(f"nextval('{new}_id_seq'::regclass)"),
        )

        op.execute(f"ALTER INDEX {old}_pkey RENAME TO {new}_pkey")

    # Foreign Keys
    op.create_foreign_key(
        "bot_coauthors_bot_id_fkey",
        "sharing_service_coauthors",
        "sharing_service_bots",
        ["sharingservice_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "sharing_service_coauthors_user_id_fkey",
        "sharing_service_coauthors",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "bot_groups_bot_id_fkey",
        "sharing_service_groups",
        "sharing_service_bots",
        ["sharingservice_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "sharing_service_groups_group_id_fkey",
        "sharing_service_groups",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "bot_group_users_bot_group_id_fkey",
        "sharing_service_group_users",
        "sharing_service_groups",
        ["sharing_service_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "sharing_service_group_users_group_user_id_fkey",
        "sharing_service_group_users",
        "group_users",
        ["group_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "sharing_service_submissions_obj_id_fkey",
        "sharing_service_submissions",
        "objs",
        ["obj_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "submissions_bot_id_fkey",
        "sharing_service_submissions",
        "sharing_service_bots",
        ["sharingservice_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "sharing_service_submissions_user_id_fkey",
        "sharing_service_submissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "stream_sharing_service_bots_sharingservice_id_fkey",
        "stream_sharing_service_bots",
        "sharing_service_bots",
        ["sharingservice_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "stream_sharing_service_bots_stream_id_fkey",
        "stream_sharing_service_bots",
        "streams",
        ["stream_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "instrument_sharing_service__sharingservice_id_fkey",
        "instrument_sharing_service_bots",
        "sharing_service_bots",
        ["sharingservice_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "instrument_sharing_service_bots_instrument_id_fkey",
        "instrument_sharing_service_bots",
        "instruments",
        ["instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    # Drop foreign key constraints
    op.drop_constraint(
        "sharing_service_submissions_user_id_fkey",
        "sharing_service_submissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "submissions_bot_id_fkey",
        "sharing_service_submissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharing_service_submissions_obj_id_fkey",
        "sharing_service_submissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharing_service_group_users_group_user_id_fkey",
        "sharing_service_group_users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "bot_group_users_bot_group_id_fkey",
        "sharing_service_group_users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharing_service_groups_group_id_fkey",
        "sharing_service_groups",
        type_="foreignkey",
    )
    op.drop_constraint(
        "bot_groups_bot_id_fkey", "sharing_service_groups", type_="foreignkey"
    )
    op.drop_constraint(
        "sharing_service_coauthors_user_id_fkey",
        "sharing_service_coauthors",
        type_="foreignkey",
    )
    op.drop_constraint(
        "bot_coauthors_bot_id_fkey",
        "sharing_service_coauthors",
        type_="foreignkey",
    )
    op.drop_constraint(
        "stream_sharing_service_bots_stream_id_fkey",
        "stream_sharing_service_bots",
        type_="foreignkey",
    )
    op.drop_constraint(
        "stream_sharing_service_bots_sharingservice_id_fkey",
        "stream_sharing_service_bots",
        type_="foreignkey",
    )
    op.drop_constraint(
        "instrument_sharing_service_bots_instrument_id_fkey",
        "instrument_sharing_service_bots",
        type_="foreignkey",
    )
    op.drop_constraint(
        "instrument_sharing_service__sharingservice_id_fkey",
        "instrument_sharing_service_bots",
        type_="foreignkey",
    )

    # sharing_service_submissions
    op.drop_column("sharing_service_submissions", "hermes_response")
    op.drop_column("sharing_service_submissions", "hermes_status")
    op.drop_column("sharing_service_submissions", "publish_to_hermes")
    op.drop_column("sharing_service_submissions", "publish_to_tns")
    op.alter_column(
        "sharing_service_submissions",
        "tns_response",
        new_column_name="response",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "sharing_service_submissions",
        "tns_payload",
        new_column_name="payload",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "sharing_service_submissions",
        "tns_submission_id",
        new_column_name="submission_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "sharing_service_submissions",
        "tns_status",
        new_column_name="status",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "sharing_service_submissions",
        "custom_publishing_string",
        new_column_name="custom_reporting_string",
        existing_type=sa.String(),
    )
    op.alter_column(
        "sharing_service_submissions",
        "sharingservice_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # sharing_service_group_users
    op.alter_column(
        "sharing_service_group_users",
        "sharing_service_group_id",
        new_column_name="tnsrobot_group_id",
        existing_type=sa.Integer(),
    )

    # sharing_service_groups
    op.drop_column("sharing_service_groups", "auto_share_to_hermes")
    op.alter_column(
        "sharing_service_groups",
        "auto_sharing_allow_bots",
        new_column_name="auto_report_allow_bots",
        existing_type=sa.Boolean(),
        existing_server_default=sa.text("false"),
    )
    op.alter_column(
        "sharing_service_groups",
        "auto_share_to_tns",
        new_column_name="auto_report",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
    )
    op.alter_column(
        "sharing_service_groups",
        "sharingservice_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # sharing_service_coauthors
    op.alter_column(
        "sharing_service_coauthors",
        "sharingservice_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # stream_sharing_service_bots
    op.alter_column(
        "stream_sharing_service_bots",
        "sharingservice_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # instrument_sharing_service_bots
    op.alter_column(
        "instrument_sharing_service_bots",
        "sharingservice_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # sharing_service_bots
    op.drop_column("sharing_service_bots", "enable_sharing_with_tns")
    op.drop_column("sharing_service_bots", "enable_sharing_with_hermes")
    op.alter_column(
        "sharing_service_bots",
        "_tns_altdata",
        new_column_name="_altdata",
        existing_type=postgresql.BYTEA(),
    )
    op.alter_column(
        "sharing_service_bots",
        "source_group_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "sharing_service_bots", "bot_id", existing_type=sa.Integer(), nullable=False
    )
    op.alter_column(
        "sharing_service_bots",
        "publish_existing_tns_objects",
        new_column_name="report_existing",
        nullable=False,
        existing_type=sa.Boolean(),
    )

    for old, new in tables_to_rename:
        # Rename tables
        op.rename_table(new, old)

        # Manage index
        op.drop_index(f"ix_{new}_created_at", table_name=old)
        op.create_index(
            f"ix_{old}_created_at",
            old,
            ["created_at"],
            unique=False,
        )
        if "instrument" in new or "stream" in new:
            op.drop_index(f"{new}_reverse_ind", table_name=old)
            op.drop_index(f"{new}_forward_ind", table_name=old)
            op.create_index(
                f"{old}_reverse_ind",
                old,
                [
                    "tnsrobot_id",
                    f"{'instrument' if 'instrument' in new else 'stream'}_id",
                ],
                unique=False,
            )
            op.create_index(
                f"{old}_forward_ind",
                old,
                [
                    f"{'instrument' if 'instrument' in new else 'stream'}_id",
                    "tnsrobot_id",
                ],
                unique=True,
            )

        # Manage sequences
        op.execute(f"ALTER SEQUENCE {new}_id_seq RENAME TO {old}_id_seq")
        op.execute(f"ALTER SEQUENCE {old}_id_seq OWNED BY {old}.id")
        op.alter_column(
            old,
            "id",
            server_default=sa.text(f"nextval('{old}_id_seq'::regclass)"),
        )

        # Rename primary keys
        op.execute(f"ALTER INDEX {new}_pkey RENAME TO {old}_pkey")

    op.create_foreign_key(
        "tnsrobot_submissions_obj_id_fkey",
        "tnsrobot_submissions",
        "objs",
        ["obj_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "tnsrobot_submissions_user_id_fkey",
        "tnsrobot_submissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "tnsrobot_submissions_tnsrobot_id_fkey",
        "tnsrobot_submissions",
        "tnsrobots",
        ["tnsrobot_id"],
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
    op.create_foreign_key(
        "tnsrobot_group_users_tnsrobot_group_id_fkey",
        "tnsrobot_group_users",
        "tnsrobot_groups",
        ["tnsrobot_group_id"],
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
    op.create_foreign_key(
        "tnsrobot_groups_tnsrobot_id_fkey",
        "tnsrobot_groups",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "tnsrobot_coauthors_user_id_fkey",
        "tnsrobot_coauthors",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "tnsrobot_coauthors_tnsrobot_id_fkey",
        "tnsrobot_coauthors",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "stream_tnsrobots_stream_id_fkey",
        "stream_tnsrobots",
        "streams",
        ["stream_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "stream_tnsrobots_tnsrobot_id_fkey",
        "stream_tnsrobots",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "instrument_tnsrobots_instrument_id_fkey",
        "instrument_tnsrobots",
        "instruments",
        ["instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "instrument_tnsrobots_tnsrobot_id_fkey",
        "instrument_tnsrobots",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
