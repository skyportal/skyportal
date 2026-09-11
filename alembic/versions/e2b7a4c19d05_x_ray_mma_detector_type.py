"""Add an x-ray MMA detector type

Einstein Probe is an X-ray mission, and its notices are already tagged X-ray;
without the value it would have to be filed as gamma-ray-burst.

Revision ID: e2b7a4c19d05
Revises: 02dff366befe
Create Date: 2026-08-23 14:00:00.000000
"""

from alembic import op

revision = "e2b7a4c19d05"
down_revision = "02dff366befe"
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE mma_detector_types ADD VALUE IF NOT EXISTS 'x-ray'")


def downgrade():
    # Postgres cannot drop an enum value; rebuilding the type would break any
    # detector already filed as x-ray.
    pass
