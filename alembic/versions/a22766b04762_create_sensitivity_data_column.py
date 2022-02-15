"""create sensitivity_data column in instrument table

Revision ID: a22766b04762
Revises: 9167685a2710
Create Date: 2022-02-15 09:01:32.376761

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'a22766b04762'
down_revision = '9167685a2710'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('instruments', sa.Column('sensitivity_data', JSONB, nullable=True))


def downgrade():
    op.drop_column('instruments', 'sensitivity_data')
