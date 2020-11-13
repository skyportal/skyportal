"""Refactor candidates table

Revision ID: fbf89710dead
Revises: d67d42b06b11
Create Date: 2020-11-12 16:34:25.642126

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fbf89710dead'
down_revision = 'd67d42b06b11'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(op.f("candidates_pkey"), "candidates")
    op.add_column(
        "candidates",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True, index=True,),
    )
    op.create_index(op.f("candidates_pkey"), "candidates", ["id"], unique=True)
    op.create_index(
        op.f("candidates_main_index"),
        "candidates",
        ["obj_id", "filter_id", "passed_at"],
        unique=True,
    )
    op.create_index(
        op.f("ix_candidates_passing_alert_id"),
        "candidates",
        ["passing_alert_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_candidates_passing_alert_id"), "candidates")
    op.drop_index(op.f("candidates_main_index"), "candidates")
    op.drop_constraint(op.f("candidates_pkey"), "candidates")
    op.drop_column("candidates", "id")
    op.drop_index(op.f("candidates_pkey"), "candidates")
    op.create_index(
        op.f("candidates_pkey"), "candidates", ["obj_id", "filter_id"], unique=True,
    )
