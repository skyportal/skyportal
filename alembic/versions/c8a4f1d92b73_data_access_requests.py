"""Add data_access_requests table

Revision ID: c8a4f1d92b73
Revises: a7c94e1d6b30
Create Date: 2026-08-25 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8a4f1d92b73"
down_revision = "e2b7c4d81f39"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "data_access_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("obj_id", sa.String(), nullable=False),
        sa.Column(
            "data_type",
            sa.Enum("photometry", "spectrum", name="data_access_request_type"),
            nullable=False,
        ),
        sa.Column("instrument_id", sa.Integer(), nullable=True),
        sa.Column("filter", sa.String(), nullable=True),
        sa.Column("spectrum_id", sa.Integer(), nullable=True),
        sa.Column(
            "owner_group_ids",
            postgresql.ARRAY(sa.Integer()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "accepted",
                "declined",
                name="data_access_request_status",
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("responded_by_id", sa.Integer(), nullable=True),
        sa.Column("granted_group_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(data_type = 'photometry' AND instrument_id IS NOT NULL "
            "AND filter IS NOT NULL AND spectrum_id IS NULL) OR "
            "(data_type = 'spectrum' AND spectrum_id IS NOT NULL "
            "AND instrument_id IS NULL AND filter IS NULL)",
            name="data_access_requests_dataset_shape",
        ),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["obj_id"], ["objs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instruments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["spectrum_id"], ["spectra.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["granted_group_id"], ["groups.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "created_at",
        "requester_id",
        "owner_id",
        "obj_id",
        "instrument_id",
        "spectrum_id",
        "status",
    ):
        op.create_index(
            op.f(f"ix_data_access_requests_{column}"),
            "data_access_requests",
            [column],
            unique=False,
        )


def downgrade():
    op.drop_table("data_access_requests")
    sa.Enum(name="data_access_request_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="data_access_request_status").drop(op.get_bind(), checkfirst=True)
