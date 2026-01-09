"""Revision description

Revision ID: bd4b9d5e489b
Revises: 9f2a7c3e1b45
Create Date: 2026-01-09 12:55:53.210614

"""

import sqlalchemy as sa
import sqlalchemy_utils

from alembic import op

# revision identifiers, used by Alembic.
revision = "bd4b9d5e489b"
down_revision = "9f2a7c3e1b45"
branch_labels = None
depends_on = None


def upgrade():
    # Ensure pg_trgm extension is available for trigram indexing
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Create an IMMUTABLE function to convert alias array to lowercase string
    # This is required because PostgreSQL needs to know the function is stable
    # for use in functional indexes
    op.execute(
        """
        CREATE OR REPLACE FUNCTION objs_alias_to_lower_text(alias text[])
        RETURNS text
        LANGUAGE sql
        IMMUTABLE
        AS $$
            SELECT lower(array_to_string(alias, ' '))
        $$;
        """
    )

    # Create GIN trigram index using the immutable function
    # This significantly improves performance for LIKE queries on aliases
    op.execute(
        """
        CREATE INDEX idx_objs_alias_gin_trgm
        ON objs
        USING gin(objs_alias_to_lower_text(alias) gin_trgm_ops);
        """
    )


def downgrade():
    # Drop the GIN trigram index
    op.execute("DROP INDEX IF EXISTS idx_objs_alias_gin_trgm;")

    # Drop the immutable function
    op.execute("DROP FUNCTION IF EXISTS objs_alias_to_lower_text(text[]);")
