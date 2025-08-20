"""Unifying TNS with hermes

Revision ID: 4e01b7c1ae61
Revises: d10af879495e
Create Date: 2025-06-19 17:24:20.538617

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "4e01b7c1ae61"
down_revision = "d10af879495e"
branch_labels = None
depends_on = None

tables_to_rename = [
    ("tnsrobots", "sharingservices"),
    ("instrument_tnsrobots", "instrument_sharingservices"),
    ("stream_tnsrobots", "stream_sharingservices"),
    ("tnsrobot_coauthors", "sharingservicecoauthors"),
    ("tnsrobot_groups", "sharingservicegroups"),
    ("tnsrobot_group_users", "sharingservicegroupautopublishers"),
    ("tnsrobot_submissions", "sharingservicesubmissions"),
]


def upgrade():
    op.execute("""
        INSERT INTO acls (id, created_at, modified)
        SELECT 'Manage sharing services', NOW(), NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM acls WHERE id='Manage sharing services'
        )
    """)

    op.execute(
        """
        UPDATE user_acls
        SET acl_id = 'Manage sharing services'
        WHERE acl_id = 'Manage TNS robots'
        """
    )

    op.execute(
        """
        DELETE FROM acls
        WHERE id='Manage TNS robots'
        """
    )

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

    # sharingservices
    op.add_column(
        "tnsrobots",
        sa.Column(
            "name",
            sa.String(),
            nullable=True,
        ),
    )
    op.execute("""UPDATE tnsrobots SET name = bot_name""")

    op.alter_column(
        "tnsrobots",
        "name",
        existing_type=sa.String(),
        nullable=False,
    )

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
    op.alter_column(
        "tnsrobots",
        "bot_name",
        new_column_name="tns_bot_name",
        existing_type=sa.String(),
        nullable=True,
    )
    op.alter_column(
        "tnsrobots",
        "bot_id",
        new_column_name="tns_bot_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "tnsrobots",
        "source_group_id",
        new_column_name="tns_source_group_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "tnsrobots",
        "_altdata",
        new_column_name="_tns_altdata",
        existing_type=postgresql.BYTEA(),
    )

    # instrument_sharingservices
    op.alter_column(
        "instrument_tnsrobots",
        "tnsrobot_id",
        new_column_name="sharing_service_id",
        existing_type=sa.Integer(),
    )

    # stream_sharingservices
    op.alter_column(
        "stream_tnsrobots",
        "tnsrobot_id",
        new_column_name="sharing_service_id",
        existing_type=sa.Integer(),
    )

    # sharingservicecoauthors
    op.alter_column(
        "tnsrobot_coauthors",
        "tnsrobot_id",
        new_column_name="sharing_service_id",
        existing_type=sa.Integer(),
    )

    # sharingservicegroups
    op.alter_column(
        "tnsrobot_groups",
        "tnsrobot_id",
        new_column_name="sharing_service_id",
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

    # sharingservicegroupautopublishers
    op.alter_column(
        "tnsrobot_group_users",
        "tnsrobot_group_id",
        new_column_name="sharing_service_group_id",
        existing_type=sa.Integer(),
    )

    # sharingservicesubmissions
    op.alter_column(
        "tnsrobot_submissions",
        "tnsrobot_id",
        new_column_name="sharing_service_id",
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
    op.execute(
        "UPDATE tnsrobot_submissions SET tns_status = NULL WHERE tns_status = 'N/A'"
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
                    "sharing_service_id",
                    f"{'instrument' if 'instrument' in new else 'stream'}_id",
                ],
                unique=False,
            )
            op.create_index(
                f"{new}_forward_ind",
                new,
                [
                    f"{'instrument' if 'instrument' in new else 'stream'}_id",
                    "sharing_service_id",
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

    # Unique constraints
    op.create_unique_constraint(None, "sharingservices", ["name"])

    # Foreign Keys
    op.create_foreign_key(
        None,
        "sharingservicecoauthors",
        "sharingservices",
        ["sharing_service_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "sharingservicecoauthors",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "sharingservicegroups",
        "sharingservices",
        ["sharing_service_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "sharingservicegroups",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "sharingservicegroupautopublishers",
        "sharingservicegroups",
        ["sharing_service_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "sharingservicegroupautopublishers",
        "group_users",
        ["group_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "sharingservicesubmissions",
        "objs",
        ["obj_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "sharingservicesubmissions",
        "sharingservices",
        ["sharing_service_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "sharingservicesubmissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "stream_sharingservices",
        "sharingservices",
        ["sharing_service_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "stream_sharingservices",
        "streams",
        ["stream_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "instrument_sharingservices",
        "sharingservices",
        ["sharing_service_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "instrument_sharingservices",
        "instruments",
        ["instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.execute(
        """
        INSERT INTO acls (id, created_at, modified)
        SELECT 'Manage TNS robots', NOW(), NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM acls WHERE id='Manage TNS robots'
        )
        """
    )

    op.execute(
        """
        UPDATE user_acls
        SET acl_id = 'Manage TNS robots'
        WHERE acl_id = 'Manage sharing services'
        """
    )

    op.execute(
        """
        DELETE
        FROM acls
        WHERE id = 'Manage sharing services'
        """
    )
    # Drop foreign key constraints
    op.drop_constraint(
        "sharingservicesubmissions_user_id_fkey",
        "sharingservicesubmissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicesubmissions_sharing_service_id_fkey",
        "sharingservicesubmissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicesubmissions_obj_id_fkey",
        "sharingservicesubmissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicegroupautopublishers_group_user_id_fkey",
        "sharingservicegroupautopublishers",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicegroupautopublishers_sharing_service_group_id_fkey",
        "sharingservicegroupautopublishers",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicegroups_group_id_fkey",
        "sharingservicegroups",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicegroups_sharing_service_id_fkey",
        "sharingservicegroups",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicecoauthors_user_id_fkey",
        "sharingservicecoauthors",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicecoauthors_sharing_service_id_fkey",
        "sharingservicecoauthors",
        type_="foreignkey",
    )
    op.drop_constraint(
        "stream_sharingservices_stream_id_fkey",
        "stream_sharingservices",
        type_="foreignkey",
    )
    op.drop_constraint(
        "stream_sharingservices_sharing_service_id_fkey",
        "stream_sharingservices",
        type_="foreignkey",
    )
    op.drop_constraint(
        "instrument_sharingservices_instrument_id_fkey",
        "instrument_sharingservices",
        type_="foreignkey",
    )
    op.drop_constraint(
        "instrument_sharingservices_sharing_service_id_fkey",
        "instrument_sharingservices",
        type_="foreignkey",
    )
    # unique constraints
    op.drop_constraint("sharingservices_name_key", "sharingservices", type_="unique")

    # sharingservicesubmissions
    op.drop_column("sharingservicesubmissions", "hermes_response")
    op.drop_column("sharingservicesubmissions", "hermes_status")
    op.drop_column("sharingservicesubmissions", "publish_to_hermes")
    op.drop_column("sharingservicesubmissions", "publish_to_tns")
    op.alter_column(
        "sharingservicesubmissions",
        "tns_response",
        new_column_name="response",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "sharingservicesubmissions",
        "tns_payload",
        new_column_name="payload",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "sharingservicesubmissions",
        "tns_submission_id",
        new_column_name="submission_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "sharingservicesubmissions",
        "tns_status",
        new_column_name="status",
        existing_type=sa.String(),
        nullable=True,
    )
    op.execute(
        "UPDATE sharingservicesubmissions SET status = 'N/A' WHERE status IS NULL"
    )
    op.alter_column(
        "sharingservicesubmissions",
        "status",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "sharingservicesubmissions",
        "custom_publishing_string",
        new_column_name="custom_reporting_string",
        existing_type=sa.String(),
    )
    op.alter_column(
        "sharingservicesubmissions",
        "sharing_service_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # sharingservicegroupautopublishers
    op.alter_column(
        "sharingservicegroupautopublishers",
        "sharing_service_group_id",
        new_column_name="tnsrobot_group_id",
        existing_type=sa.Integer(),
    )

    # sharingservicegroups
    op.drop_column("sharingservicegroups", "auto_share_to_hermes")
    op.alter_column(
        "sharingservicegroups",
        "auto_sharing_allow_bots",
        new_column_name="auto_report_allow_bots",
        existing_type=sa.Boolean(),
        existing_server_default=sa.text("false"),
    )
    op.alter_column(
        "sharingservicegroups",
        "auto_share_to_tns",
        new_column_name="auto_report",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
    )
    op.alter_column(
        "sharingservicegroups",
        "sharing_service_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # sharingservicecoauthors
    op.alter_column(
        "sharingservicecoauthors",
        "sharing_service_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # stream_sharingservices
    op.alter_column(
        "stream_sharingservices",
        "sharing_service_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # instrument_sharingservices
    op.alter_column(
        "instrument_sharingservices",
        "sharing_service_id",
        new_column_name="tnsrobot_id",
        existing_type=sa.Integer(),
    )

    # sharingservices
    op.drop_column("sharingservices", "name")
    op.drop_column("sharingservices", "enable_sharing_with_tns")
    op.drop_column("sharingservices", "enable_sharing_with_hermes")
    op.alter_column(
        "sharingservices",
        "tns_bot_name",
        new_column_name="bot_name",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "sharingservices",
        "tns_bot_id",
        new_column_name="bot_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "sharingservices",
        "tns_source_group_id",
        new_column_name="source_group_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "sharingservices",
        "_tns_altdata",
        new_column_name="_altdata",
        existing_type=postgresql.BYTEA(),
    )
    op.alter_column(
        "sharingservices", "bot_id", existing_type=sa.Integer(), nullable=False
    )
    op.alter_column(
        "sharingservices",
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
        None,
        "tnsrobot_submissions",
        "objs",
        ["obj_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "tnsrobot_submissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "tnsrobot_submissions",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "tnsrobot_group_users",
        "group_users",
        ["group_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "tnsrobot_group_users",
        "tnsrobot_groups",
        ["tnsrobot_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "tnsrobot_groups",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "tnsrobot_groups",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "tnsrobot_coauthors",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "tnsrobot_coauthors",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "stream_tnsrobots",
        "streams",
        ["stream_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "stream_tnsrobots",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "instrument_tnsrobots",
        "instruments",
        ["instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "instrument_tnsrobots",
        "tnsrobots",
        ["tnsrobot_id"],
        ["id"],
        ondelete="CASCADE",
    )
