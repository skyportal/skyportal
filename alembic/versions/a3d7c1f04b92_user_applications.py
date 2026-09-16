"""Add UserApplication table

Revision ID: a3d7c1f04b92
Revises: b2f8a1c9d3e5
Create Date: 2026-09-15 10:00:00.000000

"""

import sqlalchemy as sa
import sqlalchemy_utils

from alembic import op

# revision identifiers, used by Alembic.
revision = "a3d7c1f04b92"
down_revision = "b2f8a1c9d3e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "userapplications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column(
            "contact_email",
            sqlalchemy_utils.types.email.EmailType(length=255),
            nullable=False,
        ),
        sa.Column("affiliation", sa.String(), nullable=True),
        sa.Column("statement", sa.String(), nullable=True),
        sa.Column("endorser_email", sa.String(), nullable=True),
        sa.Column("endorser_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "endorsed", "declined", name="user_application_status"),
            nullable=False,
        ),
        sa.Column("endorsed_by_id", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decline_reason", sa.String(), nullable=True),
        sa.Column("invitation_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["endorsed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["endorser_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["invitation_id"], ["invitations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "created_at",
        "contact_email",
        "endorser_id",
        "status",
        "endorsed_by_id",
    ):
        op.create_index(
            op.f(f"ix_userapplications_{column}"),
            "userapplications",
            [column],
            unique=False,
        )


def downgrade():
    op.drop_table("userapplications")
    op.execute("DROP TYPE user_application_status")
