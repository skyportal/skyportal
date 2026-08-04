"""filter broker_id + broker defaults

Revision ID: b7e1f4a90c31
Revises: 2c4c3061af22
Create Date: 2026-08-02 18:35:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7e1f4a90c31"
down_revision = "2c4c3061af22"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("filters", sa.Column("broker_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_filters_broker_id"), "filters", ["broker_id"], unique=False
    )
    op.create_foreign_key(
        "filters_broker_id_fkey",
        "filters",
        "brokers",
        ["broker_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # BOOM was the only broker running filters so far, and a filter it runs
    # carries its binding under altdata's 'boom' key. Only those belong to it
    # (NULL if it isn't configured); every other filter stays unattached.
    op.execute(
        """
        UPDATE filters
        SET broker_id = (
            SELECT min(id) FROM brokers WHERE broker_classname = 'BOOMBROKER'
        )
        WHERE altdata ? 'boom'
        """
    )
    op.execute(
        "UPDATE filters SET altdata = altdata - 'broker_id' WHERE altdata ? 'broker_id'"
    )

    op.add_column(
        "brokers",
        sa.Column(
            "default_alert_search",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "brokers",
        sa.Column(
            "default_crossmatch", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.create_index(
        "brokers_default_alert_search",
        "brokers",
        ["default_alert_search"],
        unique=True,
        postgresql_where=sa.text("default_alert_search"),
    )
    op.create_index(
        "brokers_default_crossmatch",
        "brokers",
        ["default_crossmatch"],
        unique=True,
        postgresql_where=sa.text("default_crossmatch"),
    )
    op.execute(
        """
        UPDATE brokers
        SET default_alert_search = true, default_crossmatch = true
        WHERE id = (SELECT min(id) FROM brokers WHERE active)
        """
    )


def downgrade():
    op.drop_index("brokers_default_crossmatch", table_name="brokers")
    op.drop_index("brokers_default_alert_search", table_name="brokers")
    op.drop_column("brokers", "default_crossmatch")
    op.drop_column("brokers", "default_alert_search")
    op.execute(
        """
        UPDATE filters
        SET altdata = coalesce(altdata, '{}'::jsonb)
            || jsonb_build_object('broker_id', broker_id)
        WHERE broker_id IS NOT NULL
        """
    )
    op.drop_constraint("filters_broker_id_fkey", "filters", type_="foreignkey")
    op.drop_index(op.f("ix_filters_broker_id"), table_name="filters")
    op.drop_column("filters", "broker_id")
