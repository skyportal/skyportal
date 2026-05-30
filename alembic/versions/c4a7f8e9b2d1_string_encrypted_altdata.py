"""Migrate _altdata columns from LargeBinary to String for StringEncryptedType.

EncryptedType (deprecated) stored the AES-encrypted, base64-encoded ciphertext
as bytea via `str.encode()`. StringEncryptedType stores the same ciphertext
directly as text. The ciphertext is already valid UTF-8, so `convert_from(...,
'UTF8')` round-trips losslessly.

Revision ID: c4a7f8e9b2d1
Revises: bea830983575
Create Date: 2026-05-22 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "c4a7f8e9b2d1"
down_revision = "bea830983575"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "allocations",
        "_altdata",
        type_=sa.String(),
        existing_type=sa.LargeBinary(),
        existing_nullable=True,
        postgresql_using="convert_from(_altdata, 'UTF8')",
    )
    op.alter_column(
        "sharingservices",
        "_tns_altdata",
        type_=sa.String(),
        existing_type=sa.LargeBinary(),
        existing_nullable=True,
        postgresql_using="convert_from(_tns_altdata, 'UTF8')",
    )


def downgrade():
    op.alter_column(
        "sharingservices",
        "_tns_altdata",
        type_=sa.LargeBinary(),
        existing_type=sa.String(),
        existing_nullable=True,
        postgresql_using="convert_to(_tns_altdata, 'UTF8')",
    )
    op.alter_column(
        "allocations",
        "_altdata",
        type_=sa.LargeBinary(),
        existing_type=sa.String(),
        existing_nullable=True,
        postgresql_using="convert_to(_altdata, 'UTF8')",
    )
