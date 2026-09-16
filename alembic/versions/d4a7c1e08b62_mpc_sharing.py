"""Publish tracks to the Minor Planet Center

An MPC submission covers a whole track rather than one detection, so the
submission row hangs off the track's anchor Obj; the columns otherwise mirror
the TNS and Hermes ones.

Revision ID: d4a7c1e08b62
Revises: b2f8a1c9d3e5
Create Date: 2026-09-16

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4a7c1e08b62"
down_revision = "b2f8a1c9d3e5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sharingservices",
        sa.Column("_mpc_altdata", sa.String(), nullable=True),
    )
    op.add_column(
        "sharingservicegroups",
        sa.Column(
            "auto_share_to_mpc",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column(
            "publish_to_mpc", sa.Boolean(), server_default="false", nullable=False
        ),
    )
    op.add_column(
        "sharingservicesubmissions", sa.Column("mpc_status", sa.String(), nullable=True)
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column("mpc_submission_id", sa.String(), nullable=True),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column(
            "mpc_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column(
            "mpc_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade():
    op.drop_column("sharingservicesubmissions", "mpc_payload")
    op.drop_column("sharingservicesubmissions", "mpc_response")
    op.drop_column("sharingservicesubmissions", "mpc_submission_id")
    op.drop_column("sharingservicesubmissions", "mpc_status")
    op.drop_column("sharingservicesubmissions", "publish_to_mpc")
    op.drop_column("sharingservicegroups", "auto_share_to_mpc")
    op.drop_column("sharingservices", "_mpc_altdata")
