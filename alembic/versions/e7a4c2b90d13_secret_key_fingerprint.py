"""secret key fingerprint

app.secret_key encrypts credential columns in allocations, brokers, sharing
services and analyses, so a key that changes under a running database leaves
those rows undecryptable. This records the key in use so the app can refuse to
start on a different one.

Revision ID: e7a4c2b90d13
Revises: b8f3d21c07ae
Create Date: 2026-09-23

"""

import sqlalchemy as sa

from alembic import op

revision = "e7a4c2b90d13"
down_revision = "b8f3d21c07ae"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "secret_key_fingerprint",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="secret_key_fingerprint_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("secret_key_fingerprint")
