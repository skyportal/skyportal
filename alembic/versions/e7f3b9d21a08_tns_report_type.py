"""Which TNS report a sharing service submission files

Revision ID: e7f3b9d21a08
Revises: d5c8a2f16b47
Create Date: 2026-10-22 16:45:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e7f3b9d21a08"
down_revision = "d5c8a2f16b47"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sharingservicesubmissions",
        sa.Column(
            "tns_report_type",
            sa.String(),
            nullable=False,
            server_default="at_report",
        ),
    )


def downgrade():
    op.drop_column("sharingservicesubmissions", "tns_report_type")
