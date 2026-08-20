"""Record terms of service acceptances

Revision ID: a7e3c95d61b4
Revises: d4c17b9e5a02
Create Date: 2026-08-19 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7e3c95d61b4"
down_revision = "d4c17b9e5a02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "termsofserviceacceptances",
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("timezone('UTC', now())"),
            nullable=False,
        ),
        sa.Column(
            "modified", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "version",
            name="terms_of_service_acceptances_user_version_uniq",
        ),
    )
    op.create_index(
        op.f("ix_termsofserviceacceptances_created_at"),
        "termsofserviceacceptances",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_termsofserviceacceptances_user_id"),
        "termsofserviceacceptances",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_termsofserviceacceptances_version"),
        "termsofserviceacceptances",
        ["version"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_termsofserviceacceptances_version"),
        table_name="termsofserviceacceptances",
    )
    op.drop_index(
        op.f("ix_termsofserviceacceptances_user_id"),
        table_name="termsofserviceacceptances",
    )
    op.drop_index(
        op.f("ix_termsofserviceacceptances_created_at"),
        table_name="termsofserviceacceptances",
    )
    op.drop_table("termsofserviceacceptances")
