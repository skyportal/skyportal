"""TRT migration

Revision ID: 468435875f30
Revises: 430a8a5f3c18
Create Date: 2024-03-29 15:48:56.979223

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '468435875f30'
down_revision = '430a8a5f3c18'
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'TRTAPI' AFTER 'TESSAPI'"
        )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###