"""TNS classification reporting safeguards

Revision ID: 3843619c7b1a
Revises: b4d2e8f1c7a3
Create Date: 2026-11-18 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "3843619c7b1a"
down_revision = "b4d2e8f1c7a3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "spectra",
        sa.Column(
            "auto_report_to_tns",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "sharingservicegroups",
        sa.Column(
            "auto_share_classifications_delay_hours",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column("tns_send_after", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("sharingservicesubmissions", "tns_send_after")
    op.drop_column("sharingservicegroups", "auto_share_classifications_delay_hours")
    op.drop_column("spectra", "auto_report_to_tns")
