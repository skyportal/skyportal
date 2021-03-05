"""Add LT APIs

Revision ID: 3e1852612f34
Revises: c1354c411fab
Create Date: 2021-02-25 19:10:55.114202

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '3e1852612f34'
down_revision = 'c1354c411fab'
branch_labels = None
depends_on = None


def upgrade():
    # Add new Liverpool Telescope API values to the followup_apis ENUM type
    # Logic adapted from https://medium.com/makimo-tech-blog/upgrading-postgresqls-enum-type-with-sqlalchemy-using-alembic-migration-881af1e30abe
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'IOOAPI'")
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'IOIAPI'")
        op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'SPRATAPI'")


def downgrade():
    # PostgreSQL does not support directly dropping values from ENUM types.
    # Instead, we create a new type and replace it as the column's typing.

    # Rename current ENUM so it can be replaced
    op.execute("ALTER TYPE followup_apis RENAME TO followup_apis_old")

    # Create a new type with just the SEDM
    op.execute("CREATE TYPE followup_apis AS ENUM('SEDMAPI')")

    # Set the API classname for any database rows referring to the LT instruments to NULL
    op.execute(
        "UPDATE instruments SET api_classname = NULL WHERE api_classname IN ('IOOAPI', 'IOIAPI', 'SPRATAPI')"
    )

    # Designate the new ENUM type as the type for instruments.api_classname
    op.execute(
        (
            "ALTER TABLE instruments ALTER COLUMN api_classname TYPE followup_apis USING "
            "api_classname::text::followup_apis"
        )
    )

    # Drop old ENUM
    op.execute("DROP TYPE followup_apis_old")
