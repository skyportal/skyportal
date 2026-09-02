"""Add gcneventextractions table

Revision ID: b4e9d17c3a80
Revises: f1c4e7a92b60
Create Date: 2026-09-02 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "b4e9d17c3a80"
down_revision = "f1c4e7a92b60"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gcneventextractions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("sent_by_id", sa.Integer(), nullable=False),
        sa.Column("dateobs", sa.DateTime(), nullable=False),
        sa.Column("circular_id", sa.Integer(), nullable=True),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["sent_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dateobs"], ["gcnevents.dateobs"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("created_at", "sent_by_id", "dateobs", "circular_id", "origin"):
        op.create_index(
            op.f(f"ix_gcneventextractions_{column}"),
            "gcneventextractions",
            [column],
            unique=False,
        )


def downgrade():
    op.drop_table("gcneventextractions")
