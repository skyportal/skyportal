"""Add bot column to comments tables

Revision ID: 1f4da189227e
Revises: 84bda9d816c6
Create Date: 2021-07-06 10:54:06.164385

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1f4da189227e"
down_revision = "84bda9d816c6"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "comments",
        sa.Column("bot", sa.Boolean(), server_default="false", nullable=True),
    )
    op.add_column(
        "comments_on_spectra",
        sa.Column("bot", sa.Boolean(), server_default="false", nullable=True),
    )

    # Back-populate existing rows
    comments = sa.Table(
        "comments",
        sa.MetaData(),
        sa.Column("id", sa.Integer()),
        sa.Column("bot", sa.String()),
    )
    conn = op.get_bind()
    conn.execute(comments.update().where(comments.c.bot.is_(None)).values(bot=False))
    comments_on_spectra = sa.Table(
        "comments_on_spectra",
        sa.MetaData(),
        sa.Column("id", sa.Integer()),
        sa.Column("bot", sa.String()),
    )
    conn = op.get_bind()
    conn.execute(
        comments_on_spectra.update()
        .where(comments_on_spectra.c.bot.is_(None))
        .values(bot=False)
    )
    op.alter_column("comments", "bot", nullable=False)
    op.alter_column("comments_on_spectra", "bot", nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("comments_on_spectra", "bot")
    op.drop_column("comments", "bot")
    # ### end Alembic commands ###
