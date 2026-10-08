"""broker credential topic status

Revision ID: b7e1c4a9d320
Revises: 2ea9d9097d08
Create Date: 2026-10-08 11:40:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7e1c4a9d320"
down_revision = "2ea9d9097d08"
branch_labels = None
depends_on = None


def upgrade():
    # The table itself is created by create_all on startup, so on a database
    # that predates the brokers feature there is nothing here to alter yet.
    if "broker_credentials" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.add_column(
        "broker_credentials",
        sa.Column(
            "topic_status",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade():
    if "broker_credentials" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.drop_column("broker_credentials", "topic_status")
