"""radio and sma bandpasses

Revision ID: a7c3e9f012ab
Revises: 87b838c05b25
Create Date: 2026-08-07 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c3e9f012ab"
down_revision = "87b838c05b25"
branch_labels = None
depends_on = None


def upgrade():
    for value, after in [
        ("radio-0.34GHz", "nicerxti"),
        ("radio-1.4GHz", "radio-0.34GHz"),
        ("radio-3GHz", "radio-1.4GHz"),
        ("radio-6GHz", "radio-3GHz"),
        ("radio-10GHz", "radio-6GHz"),
        ("radio-15GHz", "radio-10GHz"),
        ("radio-22GHz", "radio-15GHz"),
        ("radio-33GHz", "radio-22GHz"),
        ("radio-45GHz", "radio-33GHz"),
        ("sma-230GHz", "radio-45GHz"),
        ("sma-345GHz", "sma-230GHz"),
        ("sma-400GHz", "sma-345GHz"),
    ]:
        op.execute(
            f"ALTER TYPE bandpasses ADD VALUE IF NOT EXISTS '{value}' AFTER '{after}'"
        )


def downgrade():
    # Postgres does not support removing enum values.
    pass
