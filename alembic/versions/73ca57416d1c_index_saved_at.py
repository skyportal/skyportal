"""index saved_at

Revision ID: 73ca57416d1c
Revises: d67d42b06b11
Create Date: 2020-11-13 14:50:06.210598

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "73ca57416d1c"
down_revision = "d67d42b06b11"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f("ix_sources_saved_at"), "sources", ["saved_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_sources_saved_at"), table_name="sources")
