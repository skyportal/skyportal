"""Refactor candidates table

Revision ID: fbf89710dead
Revises: d67d42b06b11
Create Date: 2020-11-12 16:34:25.642126

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fbf89710dead"
down_revision = "73ca57416d1c"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(op.f("candidates_pkey"), "candidates")
    op.add_column(
        "candidates",
        sa.Column(
            "id",
            sa.Integer,
            nullable=False,
            primary_key=True,
            index=True,
        ),
    )
    op.create_index(op.f("candidates_pkey"), "candidates", ["id"], unique=True)
    op.create_index(
        op.f("candidates_main_index"),
        "candidates",
        ["obj_id", "filter_id", "passed_at"],
        unique=True,
    )
    op.create_index(
        op.f("ix_candidates_passing_alert_id"),
        "candidates",
        ["passing_alert_id"],
        unique=False,
    )
    op.add_column(
        "candidates",
        sa.Column(
            "uploader_id",
            sa.Integer,
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_candidates_uploader_id"), "candidates", ["uploader_id"], unique=False
    )
    candidates = sa.Table(
        "candidates",
        sa.MetaData(),
        sa.Column("id", sa.Integer()),
        sa.Column("uploader_id", sa.Integer()),
    )
    conn = op.get_bind()
    conn.execute(
        candidates.update()
        .where(candidates.c.uploader_id.is_(None))
        .values(uploader_id=1)
    )
    op.create_foreign_key(
        None, "candidates", "users", ["uploader_id"], ["id"], ondelete="CASCADE"
    )
    op.alter_column("candidates", "uploader_id", nullable=False)
    op.create_index(
        op.f("ix_candidates_filter_id"), "candidates", ["filter_id"], unique=False
    )
    op.create_index(
        op.f("ix_candidates_obj_id"), "candidates", ["obj_id"], unique=False
    )
    op.drop_index("candidates_pkey", table_name="candidates")
    op.drop_index("candidates_reverse_ind", table_name="candidates")
    op.drop_index("ix_candidates_id", table_name="candidates")


def downgrade():
    op.drop_index(op.f("ix_candidates_passing_alert_id"), "candidates")
    op.drop_index(op.f("candidates_main_index"), "candidates")
    op.drop_constraint(op.f("candidates_pkey"), "candidates")
    op.drop_column("candidates", "id")
    op.drop_index(op.f("ix_candidates_uploader_id"), "candidates")
    op.drop_column("candidates", "uploader_id")
    op.drop_index(op.f("candidates_pkey"), "candidates")
    op.create_index(
        op.f("candidates_pkey"),
        "candidates",
        ["obj_id", "filter_id"],
        unique=True,
    )
    op.create_index("ix_candidates_id", "candidates", ["id"], unique=False)
    op.create_index(
        "candidates_reverse_ind", "candidates", ["obj_id", "filter_id"], unique=False
    )
    op.create_index("candidates_pkey", "candidates", ["id"], unique=True)
    op.drop_index(op.f("ix_candidates_obj_id"), table_name="candidates")
    op.drop_index(op.f("ix_candidates_filter_id"), table_name="candidates")
