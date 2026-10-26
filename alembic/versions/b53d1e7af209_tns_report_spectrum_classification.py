"""Which spectrum and classification a TNS report carries

Adds sharingservicesubmissions.tns_report_spectrum_id and
tns_report_classification_id. Both are nullable: left unset, the report still
takes the object's most recent spectrum and most recent human classification,
so existing submissions and the automatic path are unchanged.

Both drop to NULL rather than cascading, since deleting a spectrum should not
take a submission's record of what was reported with it.

Revision ID: b53d1e7af209
Revises: c4e9b2a71f08
Create Date: 2026-10-26 09:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b53d1e7af209"
down_revision = "c4e9b2a71f08"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sharingservicesubmissions",
        sa.Column("tns_report_spectrum_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sharingservicesubmissions",
        sa.Column("tns_report_classification_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_sharingservicesubmissions_tns_report_spectrum_id"),
        "sharingservicesubmissions",
        ["tns_report_spectrum_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sharingservicesubmissions_tns_report_classification_id"),
        "sharingservicesubmissions",
        ["tns_report_classification_id"],
        unique=False,
    )
    op.create_foreign_key(
        "sharingservicesubmissions_tns_report_spectrum_id_fkey",
        "sharingservicesubmissions",
        "spectra",
        ["tns_report_spectrum_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "sharingservicesubmissions_tns_report_classification_id_fkey",
        "sharingservicesubmissions",
        "classifications",
        ["tns_report_classification_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "sharingservicesubmissions_tns_report_classification_id_fkey",
        "sharingservicesubmissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "sharingservicesubmissions_tns_report_spectrum_id_fkey",
        "sharingservicesubmissions",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_sharingservicesubmissions_tns_report_classification_id"),
        table_name="sharingservicesubmissions",
    )
    op.drop_index(
        op.f("ix_sharingservicesubmissions_tns_report_spectrum_id"),
        table_name="sharingservicesubmissions",
    )
    op.drop_column("sharingservicesubmissions", "tns_report_classification_id")
    op.drop_column("sharingservicesubmissions", "tns_report_spectrum_id")
