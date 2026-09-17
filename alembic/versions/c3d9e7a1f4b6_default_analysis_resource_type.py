"""default_analyses.analysis_resource_type

Revision ID: c3d9e7a1f4b6
Revises: b2f8a1c9d3e5
Create Date: 2026-09-16 14:05:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d9e7a1f4b6"
down_revision = "b2f8a1c9d3e5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "default_analyses",
        sa.Column(
            "analysis_resource_type",
            sa.String(),
            nullable=False,
            server_default="obj",
        ),
    )


def downgrade():
    op.drop_column("default_analyses", "analysis_resource_type")
