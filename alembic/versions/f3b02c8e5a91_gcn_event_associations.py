"""Record coincident GcnEvent pairs

The pair is stored once, ordered by dateobs, with the objective quantities the
crossmatch computed (sky-map overlap and time separation) and a verdict a human
can revise. Reuses the gcn_event_obj_statuses vocabulary -- pending, confirmed,
ambiguous, rejected -- since it is the same review a scanner performs.

Revision ID: f3b02c8e5a91
Revises: c1d8f6b3a742
Create Date: 2026-08-23 16:30:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "f3b02c8e5a91"
down_revision = "c1d8f6b3a742"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gcneventassociations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("dateobs_1", sa.DateTime(), nullable=False),
        sa.Column("dateobs_2", sa.DateTime(), nullable=False),
        sa.Column("overlap", sa.Float(), nullable=False),
        sa.Column("consistency", sa.Float(), nullable=True),
        sa.Column("dt_days", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "confirmed",
                "ambiguous",
                "rejected",
                name="gcn_event_obj_statuses",
                create_type=False,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("confirmer_id", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["dateobs_1"], ["gcnevents.dateobs"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["dateobs_2"], ["gcnevents.dateobs"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["confirmer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dateobs_1", "dateobs_2", name="gcneventassociations_dateobs_pair_key"
        ),
        sa.CheckConstraint("dateobs_1 < dateobs_2", name="gcneventassociations_order"),
    )
    op.create_index(
        op.f("ix_gcneventassociations_created_at"),
        "gcneventassociations",
        ["created_at"],
    )
    for column in (
        "dateobs_1",
        "dateobs_2",
        "overlap",
        "consistency",
        "status",
        "confirmer_id",
    ):
        op.create_index(
            op.f(f"ix_gcneventassociations_{column}"),
            "gcneventassociations",
            [column],
        )


def downgrade():
    op.drop_table("gcneventassociations")
