"""Index the foreign keys an Obj deletion cascades through

Revision ID: 27112bd74c13
Revises: e7f3b9d21a08
Create Date: 2026-10-25 18:45:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "27112bd74c13"
down_revision = "e7f3b9d21a08"
branch_labels = None
depends_on = None

INDEXES = [
    ("scanreportitems", "obj_id"),
    ("sharingservicesubmissions", "obj_id"),
    ("obj_to_super_obj", "obj_id"),
    ("spectra", "followup_request_id"),
    ("spectra", "assignment_id"),
]


def upgrade():
    conn = op.get_bind()
    with op.get_context().autocommit_block():
        for table, column in INDEXES:
            name = f"ix_{table}_{column}"
            # A failed CONCURRENTLY build leaves an invalid index that IF NOT EXISTS would keep.
            if conn.execute(
                sa.text(
                    "SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
                    "WHERE c.relname = :name AND NOT i.indisvalid"
                ),
                {"name": name},
            ).scalar():
                conn.execute(sa.text(f"DROP INDEX CONCURRENTLY {name}"))
            op.create_index(
                op.f(name),
                table,
                [column],
                unique=False,
                if_not_exists=True,
                postgresql_concurrently=True,
            )


def downgrade():
    with op.get_context().autocommit_block():
        for table, column in INDEXES:
            op.drop_index(
                op.f(f"ix_{table}_{column}"),
                table_name=table,
                if_exists=True,
                postgresql_concurrently=True,
            )
