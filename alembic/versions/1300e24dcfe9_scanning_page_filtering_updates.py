"""scanning page filtering updates

Revision ID: 1300e24dcfe9
Revises: e1141138d4c6
Create Date: 2020-10-29 18:45:35.520499

"""
from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1300e24dcfe9'
down_revision = 'e1141138d4c6'
branch_labels = None
depends_on = None


def upgrade():
    # Data migration: takes a few steps...
    # Declare ORM table views. Note that the view contains old and new columns!
    candidates = sa.Table(
        'candidates',
        sa.MetaData(),
        sa.Column('id', sa.Integer()),
        sa.Column('passed_at', postgresql.TIMESTAMP()),  # column to be updated
        sa.Column(
            'created_at', postgresql.TIMESTAMP()
        ),  # column with the imputation values
    )
    connection = op.get_bind()

    # set candidates with a null passed at to be created_at
    connection.execute(
        candidates.update()
        .where(candidates.c.passed_at.is_(None))
        .values(passed_at=candidates.c.created_at)
    )

    op.alter_column(
        'candidates', 'passed_at', existing_type=postgresql.TIMESTAMP(), nullable=False
    )
    op.create_index(
        op.f('ix_candidates_passed_at'), 'candidates', ['passed_at'], unique=False
    )


def downgrade():
    op.drop_index(op.f('ix_candidates_passed_at'), table_name='candidates')
    op.alter_column(
        'candidates', 'passed_at', existing_type=postgresql.TIMESTAMP(), nullable=True
    )
