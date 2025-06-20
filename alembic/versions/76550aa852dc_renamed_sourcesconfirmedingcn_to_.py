"""Renamed SourcesConfirmedInGCN to SourcesInGCN and changed confirmed boolean columns to status enum column

Revision ID: 76550aa852dc
Revises: 6f853af1e900
Create Date: 2025-06-19 14:54:21.497121

"""

import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "76550aa852dc"
down_revision = "6f853af1e900"
branch_labels = None
depends_on = None


def upgrade():
    sources_in_gcn_status_enum = postgresql.ENUM(
        "confirmed",
        "rejected",
        "ambiguous",
        "pending",
        name="sources_in_gcn_status",
        create_type=False,
    )
    sources_in_gcn_status_enum.create(op.get_bind(), checkfirst=True)

    op.rename_table("sourcesconfirmedingcns", "sourcesingcns")

    op.add_column(
        "sourcesingcns",
        sa.Column(
            "status",
            sources_in_gcn_status_enum,
            nullable=False,
            server_default="pending",
        ),
    )

    connection = op.get_bind()

    connection.execute(
        sa.text("""
        UPDATE sourcesingcns
        SET status = CASE
            WHEN confirmed = true THEN 'confirmed'::sources_in_gcn_status
            WHEN confirmed = false THEN 'rejected'::sources_in_gcn_status
            WHEN confirmed IS NULL THEN 'ambiguous'::sources_in_gcn_status
            ELSE 'pending'::sources_in_gcn_status
        END
        """)
    )

    op.drop_column("sourcesingcns", "confirmed")


def downgrade():
    op.add_column("sourcesingcns", sa.Column("confirmed", sa.Boolean(), nullable=True))

    connection = op.get_bind()
    connection.execute(
        sa.text("""
        UPDATE sourcesingcns
        SET confirmed = CASE
            WHEN status = 'confirmed' THEN true
            WHEN status = 'rejected' THEN false
            WHEN status = 'ambiguous' THEN NULL
            WHEN status = 'pending' THEN NULL
            ELSE NULL
        END
        """)
    )

    op.drop_column("sourcesingcns", "status")

    sources_in_gcn_status_enum = postgresql.ENUM(
        "confirmed", "rejected", "ambiguous", "pending", name="sources_in_gcn_status"
    )
    sources_in_gcn_status_enum.drop(op.get_bind(), checkfirst=True)

    op.rename_table("sourcesingcns", "sourcesconfirmedingcns")
