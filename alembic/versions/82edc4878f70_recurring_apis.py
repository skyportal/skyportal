"""Recurring API migration

Revision ID: 82edc4878f70
Revises: fa832ea0ee8d
Create Date: 2023-01-20 16:04:25.227106

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '82edc4878f70'
down_revision = 'fa832ea0ee8d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'recurringapis',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified', sa.DateTime(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('method', sa.String(), nullable=False),
        sa.Column('next_call', sa.DateTime(), nullable=False),
        sa.Column('call_delay', sa.Float(), nullable=False),
        sa.Column('number_of_retries', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_recurringapis_created_at'),
        'recurringapis',
        ['created_at'],
        unique=False,
    )
    op.create_index(
        op.f('ix_recurringapis_next_call'), 'recurringapis', ['next_call'], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_recurringapis_next_call'), table_name='recurringapis')
    op.drop_index(op.f('ix_recurringapis_created_at'), table_name='recurringapis')
    op.drop_table('recurringapis')
    # ### end Alembic commands ###