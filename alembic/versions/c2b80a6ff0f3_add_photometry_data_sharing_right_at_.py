"""Add photometry data sharing right at group level

Revision ID: c2b80a6ff0f3
Revises: 87b838c05b25
Create Date: 2026-08-07 16:26:39.000024

"""

import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "c2b80a6ff0f3"
down_revision = "87b838c05b25"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "group_users",
        sa.Column("can_share", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "invitations",
        sa.Column("can_share_phot", postgresql.ARRAY(sa.Boolean()), nullable=True),
    )
    invitations = sa.Table(
        "invitations",
        sa.MetaData(),
        sa.Column("id", sa.Integer()),
        sa.Column("can_share_phot", postgresql.ARRAY(sa.Boolean())),
    )
    conn = op.get_bind()
    conn.execute(
        invitations.update()
        .where(invitations.c.can_share_phot.is_(None))
        .values(can_share_phot=[False])
    )
    op.alter_column("invitations", "can_share_phot", nullable=False)


def downgrade():
    op.drop_column("group_users", "can_share")
    op.drop_column("invitations", "can_share_phot")
