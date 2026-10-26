"""Automatic TNS classification reports, and holding an object back

Adds sharingservicegroups.auto_share_classifications_to_tns, which a group
opts into separately from auto_share_to_tns, and objs.withhold_from_tns, which
keeps one object off TNS. Both default to false, so no group starts reporting
classifications it did not ask to report and no object stops being shareable.

Revision ID: f2a6c81d57b3
Revises: a81f5c03b6d4
Create Date: 2026-10-25 13:45:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f2a6c81d57b3"
down_revision = "a81f5c03b6d4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sharingservicegroups",
        sa.Column(
            "auto_share_classifications_to_tns",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "objs",
        sa.Column(
            "withhold_from_tns",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade():
    op.drop_column("objs", "withhold_from_tns")
    op.drop_column("sharingservicegroups", "auto_share_classifications_to_tns")
