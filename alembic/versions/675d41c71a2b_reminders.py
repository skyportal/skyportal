"""Reminders migration

Revision ID: 675d41c71a2b
Revises: fccc7e78c7aa
Create Date: 2022-07-11 10:56:25.862884

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "675d41c71a2b"
down_revision = "fccc7e78c7aa"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=True),
        sa.Column("bot", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("next_reminder", sa.DateTime(), nullable=False),
        sa.Column("reminder_delay", sa.Float(), nullable=False),
        sa.Column("number_of_reminders", sa.Integer(), nullable=False),
        sa.Column("obj_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["obj_id"], ["objs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reminders_created_at"), "reminders", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_reminders_next_reminder"), "reminders", ["next_reminder"], unique=False
    )
    op.create_index(
        op.f("ix_reminders_number_of_reminders"),
        "reminders",
        ["number_of_reminders"],
        unique=False,
    )
    op.create_index(op.f("ix_reminders_obj_id"), "reminders", ["obj_id"], unique=False)
    op.create_index(
        op.f("ix_reminders_user_id"), "reminders", ["user_id"], unique=False
    )
    op.create_table(
        "group_reminders",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("reminder_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reminder_id"], ["reminders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "group_reminders_forward_ind",
        "group_reminders",
        ["group_id", "reminder_id"],
        unique=True,
    )
    op.create_index(
        "group_reminders_reverse_ind",
        "group_reminders",
        ["reminder_id", "group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_group_reminders_created_at"),
        "group_reminders",
        ["created_at"],
        unique=False,
    )
    op.create_table(
        "reminders_on_gcns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=True),
        sa.Column("bot", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("next_reminder", sa.DateTime(), nullable=False),
        sa.Column("reminder_delay", sa.Float(), nullable=False),
        sa.Column("number_of_reminders", sa.Integer(), nullable=False),
        sa.Column("gcn_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["gcn_id"], ["gcnevents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reminders_on_gcns_created_at"),
        "reminders_on_gcns",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_gcns_gcn_id"),
        "reminders_on_gcns",
        ["gcn_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_gcns_next_reminder"),
        "reminders_on_gcns",
        ["next_reminder"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_gcns_number_of_reminders"),
        "reminders_on_gcns",
        ["number_of_reminders"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_gcns_user_id"),
        "reminders_on_gcns",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "reminders_on_shifts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=True),
        sa.Column("bot", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("next_reminder", sa.DateTime(), nullable=False),
        sa.Column("reminder_delay", sa.Float(), nullable=False),
        sa.Column("number_of_reminders", sa.Integer(), nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reminders_on_shifts_created_at"),
        "reminders_on_shifts",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_shifts_next_reminder"),
        "reminders_on_shifts",
        ["next_reminder"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_shifts_number_of_reminders"),
        "reminders_on_shifts",
        ["number_of_reminders"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_shifts_shift_id"),
        "reminders_on_shifts",
        ["shift_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_shifts_user_id"),
        "reminders_on_shifts",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "group_reminders_on_gcns",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("reminders_on_gcn_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reminders_on_gcn_id"], ["reminders_on_gcns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "group_reminders_on_gcns_forward_ind",
        "group_reminders_on_gcns",
        ["group_id", "reminders_on_gcn_id"],
        unique=True,
    )
    op.create_index(
        "group_reminders_on_gcns_reverse_ind",
        "group_reminders_on_gcns",
        ["reminders_on_gcn_id", "group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_group_reminders_on_gcns_created_at"),
        "group_reminders_on_gcns",
        ["created_at"],
        unique=False,
    )
    op.create_table(
        "group_reminders_on_shifts",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("reminders_on_shift_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reminders_on_shift_id"], ["reminders_on_shifts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "group_reminders_on_shifts_forward_ind",
        "group_reminders_on_shifts",
        ["group_id", "reminders_on_shift_id"],
        unique=True,
    )
    op.create_index(
        "group_reminders_on_shifts_reverse_ind",
        "group_reminders_on_shifts",
        ["reminders_on_shift_id", "group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_group_reminders_on_shifts_created_at"),
        "group_reminders_on_shifts",
        ["created_at"],
        unique=False,
    )
    op.create_table(
        "reminders_on_spectra",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=True),
        sa.Column("bot", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("next_reminder", sa.DateTime(), nullable=False),
        sa.Column("reminder_delay", sa.Float(), nullable=False),
        sa.Column("number_of_reminders", sa.Integer(), nullable=False),
        sa.Column("obj_id", sa.String(), nullable=False),
        sa.Column("spectrum_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["obj_id"], ["objs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spectrum_id"], ["spectra.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reminders_on_spectra_created_at"),
        "reminders_on_spectra",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_spectra_next_reminder"),
        "reminders_on_spectra",
        ["next_reminder"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_spectra_number_of_reminders"),
        "reminders_on_spectra",
        ["number_of_reminders"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_spectra_obj_id"),
        "reminders_on_spectra",
        ["obj_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_spectra_spectrum_id"),
        "reminders_on_spectra",
        ["spectrum_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reminders_on_spectra_user_id"),
        "reminders_on_spectra",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "group_reminders_on_spectra",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("reminders_on_spectr_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reminders_on_spectr_id"], ["reminders_on_spectra.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "group_reminders_on_spectra_forward_ind",
        "group_reminders_on_spectra",
        ["group_id", "reminders_on_spectr_id"],
        unique=True,
    )
    op.create_index(
        "group_reminders_on_spectra_reverse_ind",
        "group_reminders_on_spectra",
        ["reminders_on_spectr_id", "group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_group_reminders_on_spectra_created_at"),
        "group_reminders_on_spectra",
        ["created_at"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_group_reminders_on_spectra_created_at"),
        table_name="group_reminders_on_spectra",
    )
    op.drop_index(
        "group_reminders_on_spectra_reverse_ind",
        table_name="group_reminders_on_spectra",
    )
    op.drop_index(
        "group_reminders_on_spectra_forward_ind",
        table_name="group_reminders_on_spectra",
    )
    op.drop_table("group_reminders_on_spectra")
    op.drop_index(
        op.f("ix_reminders_on_spectra_user_id"), table_name="reminders_on_spectra"
    )
    op.drop_index(
        op.f("ix_reminders_on_spectra_spectrum_id"), table_name="reminders_on_spectra"
    )
    op.drop_index(
        op.f("ix_reminders_on_spectra_obj_id"), table_name="reminders_on_spectra"
    )
    op.drop_index(
        op.f("ix_reminders_on_spectra_number_of_reminders"),
        table_name="reminders_on_spectra",
    )
    op.drop_index(
        op.f("ix_reminders_on_spectra_next_reminder"), table_name="reminders_on_spectra"
    )
    op.drop_index(
        op.f("ix_reminders_on_spectra_created_at"), table_name="reminders_on_spectra"
    )
    op.drop_table("reminders_on_spectra")
    op.drop_index(
        op.f("ix_group_reminders_on_shifts_created_at"),
        table_name="group_reminders_on_shifts",
    )
    op.drop_index(
        "group_reminders_on_shifts_reverse_ind", table_name="group_reminders_on_shifts"
    )
    op.drop_index(
        "group_reminders_on_shifts_forward_ind", table_name="group_reminders_on_shifts"
    )
    op.drop_table("group_reminders_on_shifts")
    op.drop_index(
        op.f("ix_group_reminders_on_gcns_created_at"),
        table_name="group_reminders_on_gcns",
    )
    op.drop_index(
        "group_reminders_on_gcns_reverse_ind", table_name="group_reminders_on_gcns"
    )
    op.drop_index(
        "group_reminders_on_gcns_forward_ind", table_name="group_reminders_on_gcns"
    )
    op.drop_table("group_reminders_on_gcns")
    op.drop_index(
        op.f("ix_reminders_on_shifts_user_id"), table_name="reminders_on_shifts"
    )
    op.drop_index(
        op.f("ix_reminders_on_shifts_shift_id"), table_name="reminders_on_shifts"
    )
    op.drop_index(
        op.f("ix_reminders_on_shifts_number_of_reminders"),
        table_name="reminders_on_shifts",
    )
    op.drop_index(
        op.f("ix_reminders_on_shifts_next_reminder"), table_name="reminders_on_shifts"
    )
    op.drop_index(
        op.f("ix_reminders_on_shifts_created_at"), table_name="reminders_on_shifts"
    )
    op.drop_table("reminders_on_shifts")
    op.drop_index(op.f("ix_reminders_on_gcns_user_id"), table_name="reminders_on_gcns")
    op.drop_index(
        op.f("ix_reminders_on_gcns_number_of_reminders"), table_name="reminders_on_gcns"
    )
    op.drop_index(
        op.f("ix_reminders_on_gcns_next_reminder"), table_name="reminders_on_gcns"
    )
    op.drop_index(op.f("ix_reminders_on_gcns_gcn_id"), table_name="reminders_on_gcns")
    op.drop_index(
        op.f("ix_reminders_on_gcns_created_at"), table_name="reminders_on_gcns"
    )
    op.drop_table("reminders_on_gcns")
    op.drop_index(op.f("ix_group_reminders_created_at"), table_name="group_reminders")
    op.drop_index("group_reminders_reverse_ind", table_name="group_reminders")
    op.drop_index("group_reminders_forward_ind", table_name="group_reminders")
    op.drop_table("group_reminders")
    op.drop_index(op.f("ix_reminders_user_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_obj_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_number_of_reminders"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_next_reminder"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_created_at"), table_name="reminders")
    op.drop_table("reminders")
    # ### end Alembic commands ###
