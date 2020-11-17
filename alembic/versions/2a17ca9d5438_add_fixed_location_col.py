"""add fixed-location column

Revision ID: 2a17ca9d5438
Revises: fbf89710dead
Create Date: 2020-11-17 14:28:10.158404

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a17ca9d5438'
down_revision = 'fbf89710dead'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'telescopes',
        sa.Column(
            'fixed_location', sa.Boolean(), server_default='true', nullable=False
        ),
    )


def downgrade():
    op.drop_column('telescopes', 'fixed_location')
