"""drop timestamp server defaults

Revision ID: dbb949db3e2c
Revises: 70db7c9f5f83
Create Date: 2026-10-14 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "dbb949db3e2c"
down_revision = "70db7c9f5f83"
branch_labels = None
depends_on = None

# Base sets these in Python, so a database built from the models has no default.
DEFAULTS = {
    ("gcneventassociations", "created_at"): "now()",
    ("gcneventassociations", "modified"): "now()",
    ("gcnassociationrules", "created_at"): "now()",
    ("gcnassociationrules", "modified"): "now()",
    ("termsofserviceacceptances", "created_at"): "timezone('UTC', now())",
    ("termsofserviceacceptances", "modified"): "now()",
}


def upgrade():
    for table, column in DEFAULTS:
        op.alter_column(table, column, server_default=None)


def downgrade():
    for (table, column), default in DEFAULTS.items():
        op.alter_column(table, column, server_default=sa.text(default))
