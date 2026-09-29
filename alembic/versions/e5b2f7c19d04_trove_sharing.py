"""Publish sources and photometry to TROVE

TROVE upserts a target on its name and returns no submission id, so the
columns mirror the Hermes ones rather than the TNS ones.

Revision ID: e5b2f7c19d04
Revises: 2db498b66cfd
Create Date: 2026-09-29

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5b2f7c19d04"
down_revision = "2db498b66cfd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sharingservices",
        sa.Column(
            "enable_sharing_with_trove",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "sharingservices",
        sa.Column("_trove_altdata", sa.String(), nullable=True),
    )
    op.add_column(
        "sharingservicegroups",
        sa.Column(
            "auto_share_to_trove",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column(
            "publish_to_trove", sa.Boolean(), server_default="false", nullable=False
        ),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column("trove_status", sa.String(), nullable=True),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column(
            "trove_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column(
            "trove_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade():
    op.drop_column("sharingservicesubmissions", "trove_payload")
    op.drop_column("sharingservicesubmissions", "trove_response")
    op.drop_column("sharingservicesubmissions", "trove_status")
    op.drop_column("sharingservicesubmissions", "publish_to_trove")
    op.drop_column("sharingservicegroups", "auto_share_to_trove")
    op.drop_column("sharingservices", "_trove_altdata")
    op.drop_column("sharingservices", "enable_sharing_with_trove")
