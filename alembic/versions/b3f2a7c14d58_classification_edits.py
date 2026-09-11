"""Add classificationedits table

Records probability changes made to an existing classification, so that
updating a classification in place keeps a trace of who changed what (#3601).

Revision ID: b3f2a7c14d58
Revises: d4e8b1c07f39
Create Date: 2026-08-15 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "b3f2a7c14d58"
down_revision = "d4e8b1c07f39"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "classificationedits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("classification_id", sa.Integer(), nullable=False),
        sa.Column("editor_id", sa.Integer(), nullable=False),
        sa.Column("editor_name", sa.String(), nullable=False),
        sa.Column("old_probability", sa.Float(), nullable=True),
        sa.Column("new_probability", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["classification_id"], ["classifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["editor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classificationedits_classification_id"),
        "classificationedits",
        ["classification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classificationedits_created_at"),
        "classificationedits",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classificationedits_editor_id"),
        "classificationedits",
        ["editor_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_classificationedits_editor_id"), table_name="classificationedits"
    )
    op.drop_index(
        op.f("ix_classificationedits_created_at"), table_name="classificationedits"
    )
    op.drop_index(
        op.f("ix_classificationedits_classification_id"),
        table_name="classificationedits",
    )
    op.drop_table("classificationedits")
