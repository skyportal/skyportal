"""Per-user cuts for event-to-event associations

Which pairs of messengers count as coincident is a science choice, not a display
preference, so it lives in its own table rather than in User.preferences.

Revision ID: a7c94e1d6b30
Revises: f3b02c8e5a91
Create Date: 2026-08-23 16:45:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "a7c94e1d6b30"
down_revision = "f3b02c8e5a91"
branch_labels = None
depends_on = None

MESSENGER = sa.Enum(
    "gravitational-wave",
    "neutrino",
    "gamma-ray-burst",
    "x-ray",
    name="mma_detector_types",
    create_type=False,
)


def upgrade():
    op.create_table(
        "gcnassociationrules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "modified", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("detector_type_1", MESSENGER, nullable=False),
        sa.Column("detector_type_2", MESSENGER, nullable=False),
        sa.Column("days", sa.Float(), nullable=False),
        sa.Column("min_consistency", sa.Float(), server_default="0.5", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "detector_type_1",
            "detector_type_2",
            name="gcnassociationrules_user_pair_key",
        ),
    )
    op.create_index(
        op.f("ix_gcnassociationrules_created_at"), "gcnassociationrules", ["created_at"]
    )
    op.create_index(
        op.f("ix_gcnassociationrules_user_id"), "gcnassociationrules", ["user_id"]
    )


def downgrade():
    op.drop_table("gcnassociationrules")
