"""add spectrumreducers and spectrumobservers

Revision ID: f94174183e7e
Revises: d0195eb7ecd0
Create Date: 2020-10-27 23:59:14.316018

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f94174183e7e'
down_revision = 'd0195eb7ecd0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'spectrum_observers',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified', sa.DateTime(), nullable=False),
        sa.Column('spectr_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['spectr_id'], ['spectra.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('spectr_id', 'user_id'),
    )
    op.create_index(
        'spectrum_observers_reverse_ind',
        'spectrum_observers',
        ['user_id', 'spectr_id'],
        unique=False,
    )
    op.create_table(
        'spectrum_reducers',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified', sa.DateTime(), nullable=False),
        sa.Column('spectr_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['spectr_id'], ['spectra.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('spectr_id', 'user_id'),
    )
    op.create_index(
        'spectrum_reducers_reverse_ind',
        'spectrum_reducers',
        ['user_id', 'spectr_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('spectrum_reducers_reverse_ind', table_name='spectrum_reducers')
    op.drop_table('spectrum_reducers')
    op.drop_index('spectrum_observers_reverse_ind', table_name='spectrum_observers')
    op.drop_table('spectrum_observers')
