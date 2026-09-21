"""analysis dropdown sections: gw_search + period_finding

Revision ID: 2db498b66cfd
Revises: c9f1b3d75a24
Create Date: 2026-09-21 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "2db498b66cfd"
down_revision = "c9f1b3d75a24"
branch_labels = None
depends_on = None


def upgrade():
    # New AnalysisService category labels; the dropdown groups by analysis_type.
    op.execute("ALTER TYPE analysistypes ADD VALUE IF NOT EXISTS 'gw_search'")
    op.execute("ALTER TYPE analysistypes ADD VALUE IF NOT EXISTS 'period_finding'")


def downgrade():
    # Postgres has no ALTER TYPE ... DROP VALUE; leaving the labels in place is
    # harmless (nothing references them once services are re-filed).
    pass
