"""Numpy 2 migration

Revision ID: 2b8addba3e86
Revises: 9a7b5f6aa515
Create Date: 2026-04-04 19:37:59.107180

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "2b8addba3e86"
down_revision = "9a7b5f6aa515"
branch_labels = None
depends_on = None


def upgrade():
    new_values = {
        "tess": ["galex::fuv", "galex::nuv"],
        "gotor": [
            "skymapperu",
            "skymapperg",
            "skymapperr",
            "skymapperi",
            "skymapperz",
            "ztf::g",
            "ztf::r",
            "ztf::i",
            "megacam6::g",
            "megacam6::r",
            "megacam6::i",
            "megacam6::i2",
            "megacam6::z",
            "hsc::g",
            "hsc::r",
            "hsc::r2",
            "hsc::i",
            "hsc::i2",
            "hsc::z",
            "hsc::y",
        ],
    }

    with op.get_context().autocommit_block():
        for after, values in new_values.items():
            for value in values:
                op.execute(
                    f"ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS '{value}' AFTER '{after}'"
                )
                after = value


def downgrade():
    pass
