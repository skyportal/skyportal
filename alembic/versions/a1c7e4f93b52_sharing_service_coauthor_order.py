"""Sharing service coauthor order

Revision ID: a1c7e4f93b52
Revises: c4d81f2a6b03
Create Date: 2026-09-14

"""

import sqlalchemy as sa

from alembic import op

revision = "a1c7e4f93b52"
down_revision = "c4d81f2a6b03"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sharingservicecoauthors",
        sa.Column("order", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        """
        UPDATE sharingservicecoauthors AS c
        SET "order" = ranked.position
        FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY sharing_service_id ORDER BY id
            ) - 1 AS position
            FROM sharingservicecoauthors
        ) AS ranked
        WHERE c.id = ranked.id
        """
    )


def downgrade():
    op.drop_column("sharingservicecoauthors", "order")
