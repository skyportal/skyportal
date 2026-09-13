"""Give MMADetectors aliases

Notices do not agree on a detector's name: GCN tags Fermi-GBM alerts "Fermi"
while the detector's nickname is "FermiGBM", so nickname-only matching linked
none of them.

Revision ID: c1d8f6b3a742
Revises: e2b7a4c19d05
Create Date: 2026-08-23 14:20:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "c1d8f6b3a742"
down_revision = "e2b7a4c19d05"
branch_labels = None
depends_on = None

# nickname -> names notices actually use for it
ALIASES = {
    "FermiGBM": ["Fermi", "Fermi-GBM", "GBM"],
    "Swift": ["Swift-BAT", "BAT", "GUANO"],
    "IceCube": ["IceCube-Gold", "IceCube-Bronze"],
    "EP": ["Einstein Probe", "WXT"],
}


def upgrade():
    op.add_column(
        "mmadetectors",
        sa.Column(
            "aliases",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )

    for nickname, aliases in ALIASES.items():
        op.execute(
            sa.text(
                "UPDATE mmadetectors SET aliases = :aliases WHERE nickname = :nickname"
            ).bindparams(aliases=aliases, nickname=nickname)
        )


def downgrade():
    op.drop_column("mmadetectors", "aliases")
