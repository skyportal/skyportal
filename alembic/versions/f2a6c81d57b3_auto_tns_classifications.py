"""Automatic TNS classification reports, and holding an object back

Adds sharingservicegroups.auto_share_classifications_to_tns, which a group
opts into separately from auto_share_to_tns, and objs.withhold_from_tns, which
keeps one object off TNS. Both default to false, so no group starts reporting
classifications it did not ask to report and no object stops being shareable.
objs.withhold_from_tns_set_by_id and objs.withhold_from_tns_set_at record who
last touched the flag.

Revision ID: f2a6c81d57b3
Revises: b53d1e7af209
Create Date: 2026-10-25 13:45:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f2a6c81d57b3"
down_revision = "b53d1e7af209"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sharingservicegroups",
        sa.Column(
            "auto_share_classifications_to_tns",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "objs",
        sa.Column(
            "withhold_from_tns",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "objs",
        sa.Column("withhold_from_tns_set_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "objs",
        sa.Column("withhold_from_tns_set_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "objs_withhold_from_tns_set_by_id_fkey",
        "objs",
        "users",
        ["withhold_from_tns_set_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "objs_withhold_from_tns_set_by_id_fkey", "objs", type_="foreignkey"
    )
    op.drop_column("objs", "withhold_from_tns_set_at")
    op.drop_column("objs", "withhold_from_tns_set_by_id")
    op.drop_column("objs", "withhold_from_tns")
    op.drop_column("sharingservicegroups", "auto_share_classifications_to_tns")
