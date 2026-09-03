"""group auto_accept_requests and stream auto_join

Revision ID: 363f77c7a441
Revises: 3d9f7a1c2b45
Create Date: 2026-07-04 16:14:45.195770

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "363f77c7a441"
down_revision = "3d9f7a1c2b45"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "groups",
        sa.Column(
            "auto_accept_requests",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "streams",
        sa.Column(
            "auto_join",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade():
    op.drop_column("streams", "auto_join")
    op.drop_column("groups", "auto_accept_requests")
