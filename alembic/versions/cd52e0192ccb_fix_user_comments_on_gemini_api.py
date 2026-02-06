"""Fix user comments on gemini api

Revision ID: cd52e0192ccb
Revises: a3953142b501
Create Date: 2026-02-06 12:18:47.640531

"""

import json

import sqlalchemy as sa
from sqlalchemy_utils.types import JSONType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine, EncryptedType

from alembic import op
from baselayer.app.env import load_env

_, cfg = load_env()

# revision identifiers, used by Alembic.
revision = "cd52e0192ccb"
down_revision = "a3953142b501"
branch_labels = None
depends_on = None

# Temporary table references for the migration
allocations = sa.table(
    "allocations",
    sa.column("id", sa.Integer),
    sa.column("instrument_id", sa.Integer),
    sa.column(
        "_altdata",
        EncryptedType(JSONType, cfg["app.secret_key"], AesEngine, "pkcs5"),
    ),
)

instruments = sa.table(
    "instruments",
    sa.column("id", sa.Integer),
    sa.column("api_classname", sa.String),
    sa.column("api_classname_obsplan", sa.String),
)


# Find all allocations using the Gemini API and retrieve their altdata
def get_gemini_allocations(connection):
    return connection.execute(
        sa.select(allocations.c.id, allocations.c._altdata)
        .select_from(
            allocations.join(
                instruments,
                allocations.c.instrument_id == instruments.c.id,
            )
        )
        .where(
            sa.or_(
                instruments.c.api_classname == "GEMINIAPI",
                instruments.c.api_classname_obsplan == "GEMINIAPI",
            )
        )
    ).fetchall()


def upgrade():
    connection = op.get_bind()

    for allocation_id, altdata_raw in get_gemini_allocations(connection):
        if altdata_raw is None:
            continue
        altdata = (
            json.loads(altdata_raw) if isinstance(altdata_raw, str) else altdata_raw
        )
        if not isinstance(altdata, dict):
            continue
        if "user_password" not in altdata:
            continue

        # Rename user_password -> user_key
        altdata["user_key"] = altdata.pop("user_password")

        connection.execute(
            allocations.update()
            .where(allocations.c.id == allocation_id)
            .values(_altdata=json.dumps(altdata))
        )


def downgrade():
    connection = op.get_bind()

    for allocation_id, altdata_raw in get_gemini_allocations(connection):
        if altdata_raw is None:
            continue
        altdata = (
            json.loads(altdata_raw) if isinstance(altdata_raw, str) else altdata_raw
        )
        if not isinstance(altdata, dict):
            continue
        if "user_key" not in altdata:
            continue

        # Rename user_key -> user_password
        altdata["user_password"] = altdata.pop("user_key")

        connection.execute(
            allocations.update()
            .where(allocations.c.id == allocation_id)
            .values(_altdata=json.dumps(altdata))
        )
