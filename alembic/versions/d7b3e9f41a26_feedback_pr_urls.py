"""feedback pull requests

Revision ID: d7b3e9f41a26
Revises: f185c756a7eb
Create Date: 2026-11-23

"""

import sqlalchemy as sa

from alembic import op

revision = "d7b3e9f41a26"
down_revision = "f185c756a7eb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "feedbacks",
        sa.Column(
            "pr_urls", sa.ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
    )
    op.add_column("feedbacks", sa.Column("deployed_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("feedbacks", "deployed_at")
    op.drop_column("feedbacks", "pr_urls")
