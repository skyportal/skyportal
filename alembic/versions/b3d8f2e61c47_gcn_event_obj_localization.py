"""Record the localization an obj was matched in for a GCN event

Revision ID: b3d8f2e61c47
Revises: 7d2c4e9a1b30
Create Date: 2026-11-20 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "b3d8f2e61c47"
down_revision = "7d2c4e9a1b30"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "gcneventobjs",
        sa.Column("localization_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_gcneventobjs_localization_id"),
        "gcneventobjs",
        ["localization_id"],
        unique=False,
    )
    op.create_foreign_key(
        "gcneventobjs_localization_id_fkey",
        "gcneventobjs",
        "localizations",
        ["localization_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "gcneventobjs_localization_id_fkey", "gcneventobjs", type_="foreignkey"
    )
    op.drop_index(op.f("ix_gcneventobjs_localization_id"), table_name="gcneventobjs")
    op.drop_column("gcneventobjs", "localization_id")
