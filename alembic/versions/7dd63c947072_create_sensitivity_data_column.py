"""create sensitivity data column
Revision ID: 7dd63c947072
Revises: 415cd17ac788
Create Date: 2022-02-24 09:47:20.742186
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7dd63c947072'
down_revision = '415cd17ac788'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'instruments',
        sa.Column(
            'sensitivity_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('instruments', 'sensitivity_data')
    # ### end Alembic commands ###