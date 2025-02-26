"""Colibri migration

Revision ID: fcc48485cb52
Revises: b0f0b2a30357
Create Date: 2024-08-28 01:12:28.594050

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "fcc48485cb52"
down_revision = "b0f0b2a30357"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'COLIBRIAPI' AFTER 'ATLASAPI'"
        )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
