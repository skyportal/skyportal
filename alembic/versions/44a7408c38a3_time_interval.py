"""Time interval

Revision ID: 44a7408c38a3
Revises: 4822ff118a4f
Create Date: 2022-09-08 20:43:42.716358

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = '44a7408c38a3'
down_revision = '99de544181a3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'mmadetectortimeintervals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified', sa.DateTime(), nullable=False),
        sa.Column('detector_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column(
            'time_interval',
            sqlalchemy_utils.types.range.DateTimeRangeType(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ['detector_id'], ['mmadetectors.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_mmadetectortimeintervals_created_at'),
        'mmadetectortimeintervals',
        ['created_at'],
        unique=False,
    )
    op.create_index(
        op.f('ix_mmadetectortimeintervals_detector_id'),
        'mmadetectortimeintervals',
        ['detector_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_mmadetectortimeintervals_owner_id'),
        'mmadetectortimeintervals',
        ['owner_id'],
        unique=False,
    )
    op.create_table(
        'group_mmadetector_time_intervals',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('mmadetectortimeinterval_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['mmadetectortimeinterval_id'],
            ['mmadetectortimeintervals.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'group_mmadetector_time_intervals_forward_ind',
        'group_mmadetector_time_intervals',
        ['group_id', 'mmadetectortimeinterval_id'],
        unique=True,
    )
    op.create_index(
        'group_mmadetector_time_intervals_reverse_ind',
        'group_mmadetector_time_intervals',
        ['mmadetectortimeinterval_id', 'group_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_group_mmadetector_time_intervals_created_at'),
        'group_mmadetector_time_intervals',
        ['created_at'],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f('ix_group_mmadetector_time_intervals_created_at'),
        table_name='group_mmadetector_time_intervals',
    )
    op.drop_index(
        'group_mmadetector_time_intervals_reverse_ind',
        table_name='group_mmadetector_time_intervals',
    )
    op.drop_index(
        'group_mmadetector_time_intervals_forward_ind',
        table_name='group_mmadetector_time_intervals',
    )
    op.drop_table('group_mmadetector_time_intervals')
    op.drop_index(
        op.f('ix_mmadetectortimeintervals_owner_id'),
        table_name='mmadetectortimeintervals',
    )
    op.drop_index(
        op.f('ix_mmadetectortimeintervals_detector_id'),
        table_name='mmadetectortimeintervals',
    )
    op.drop_index(
        op.f('ix_mmadetectortimeintervals_created_at'),
        table_name='mmadetectortimeintervals',
    )
    op.drop_table('mmadetectortimeintervals')
    # ### end Alembic commands ###