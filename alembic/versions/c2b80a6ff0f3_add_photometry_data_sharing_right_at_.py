"""Add photometry data sharing right at group level

Revision ID: c2b80a6ff0f3
Revises: c7d1a4e9f3b2
Create Date: 2026-08-07 16:26:39.000024

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "c2b80a6ff0f3"
down_revision = "c7d1a4e9f3b2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "group_users",
        sa.Column(
            "can_share_photometry", sa.Boolean(), server_default="false", nullable=False
        ),
    )
    op.add_column(
        "invitations",
        sa.Column(
            "can_share_photometry_for_groups",
            postgresql.ARRAY(sa.Boolean()),
            nullable=True,
        ),
    )
    # One entry per group, matching the other per-group arrays: onboarding
    # zips them together, so a shorter array would drop group memberships.
    op.execute(
        "UPDATE invitations "
        "SET can_share_photometry_for_groups = array_fill(false, "
        "ARRAY[coalesce(array_length(admin_for_groups, 1), 0)]) "
        "WHERE can_share_photometry_for_groups IS NULL"
    )
    op.alter_column("invitations", "can_share_photometry_for_groups", nullable=False)


def downgrade():
    op.drop_column("group_users", "can_share_photometry")
    op.drop_column("invitations", "can_share_photometry_for_groups")
