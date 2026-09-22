"""assistant message notify recipients (and merge the two open heads)

Revision ID: b7f3a2c1d4e5
Revises: 2db498b66cfd, c8d1e9f4a2b7
Create Date: 2026-09-22 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7f3a2c1d4e5"
down_revision = ("2db498b66cfd", "c8d1e9f4a2b7")
branch_labels = None
depends_on = None


def upgrade():
    # Who to notify with the answer once it is ready: {"users": [...], "groups": [...]}.
    op.add_column(
        "assistantmessages",
        sa.Column("notify", JSONB, nullable=True),
    )


def downgrade():
    op.drop_column("assistantmessages", "notify")
