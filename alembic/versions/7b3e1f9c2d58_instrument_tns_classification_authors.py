"""Authors of an instrument's TNS classification reports

Revision ID: 7b3e1f9c2d58
Revises: 3d9f6b2e8a41
Create Date: 2026-11-05 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "7b3e1f9c2d58"
down_revision = "3d9f6b2e8a41"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "instruments",
        sa.Column("tns_classification_authors", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_column("instruments", "tns_classification_authors")
