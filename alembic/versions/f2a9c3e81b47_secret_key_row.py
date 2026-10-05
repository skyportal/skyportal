"""the secret key itself, where no config names one

app.secret_key encrypts credential columns, so every process has to agree on
it. An operator who sets one in the config owns it and this table stays
empty; where none is set the database decides, which is what lets replicas
agree without sharing a volume.

Revision ID: f2a9c3e81b47
Revises: e7a4c2b90d13
Create Date: 2026-09-23

"""

import sqlalchemy as sa

from alembic import op

revision = "f2a9c3e81b47"
down_revision = "e7a4c2b90d13"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "secret_key",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="secret_key_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("secret_key")
