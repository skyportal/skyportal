"""assistant tool calls and proposal

The assistant reaches an answer by running MCP tools, and until now only its
prose survived. Recording the calls lets the page show what the answer rests
on, and a filter pipeline it arrived at can be offered for saving.

Revision ID: b8f3d21c07ae
Revises: c9e4b7a21f68
Create Date: 2026-09-23

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b8f3d21c07ae"
down_revision = "c9e4b7a21f68"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "assistantmessages",
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "assistantmessages",
        sa.Column("proposal", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column("assistantmessages", "proposal")
    op.drop_column("assistantmessages", "tool_calls")
