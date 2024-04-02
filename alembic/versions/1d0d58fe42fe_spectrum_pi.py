"""Spectrum PI migration

Revision ID: 1d0d58fe42fe
Revises: c44be702d604
Create Date: 2024-02-02 13:58:27.014325

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1d0d58fe42fe'
down_revision = 'c44be702d604'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'spectrum_pis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('spectr_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified', sa.DateTime(), nullable=False),
        sa.Column('external_pi', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['spectr_id'], ['spectra.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_spectrum_pis_created_at'), 'spectrum_pis', ['created_at'], unique=False
    )
    op.create_index(
        'spectrum_pis_forward_ind',
        'spectrum_pis',
        ['spectr_id', 'user_id'],
        unique=True,
    )
    op.create_index(
        'spectrum_pis_reverse_ind',
        'spectrum_pis',
        ['user_id', 'spectr_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('spectrum_pis_reverse_ind', table_name='spectrum_pis')
    op.drop_index('spectrum_pis_forward_ind', table_name='spectrum_pis')
    op.drop_index(op.f('ix_spectrum_pis_created_at'), table_name='spectrum_pis')
    op.drop_table('spectrum_pis')
