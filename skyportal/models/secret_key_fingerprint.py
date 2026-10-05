"""The key the database's encrypted columns were written under.

app.secret_key encrypts credential columns in allocations, brokers, sharing
services and analyses, so a key that changes under a running database leaves
those rows undecryptable -- surfacing as an InvalidPaddingError somewhere in a
later request. Recording the key in use turns that into a refusal to start.
"""

import hashlib
import sys

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from baselayer.app.models import Base

__all__ = ["SecretKeyFingerprint", "check_secret_key", "fingerprint"]


# One row, so the key the encrypted columns were written under is recorded once.
SecretKeyFingerprint = sa.Table(
    "secret_key_fingerprint",
    Base.metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
    sa.Column("fingerprint", sa.Text, nullable=False),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
    sa.CheckConstraint("id = 1", name="secret_key_fingerprint_singleton"),
)

CHANGED = (
    "app.secret_key is not the key this database was last started on. It "
    "encrypts the credentials stored in allocations, brokers, sharing services "
    "and analyses, so those rows can no longer be decrypted and will raise "
    "InvalidPaddingError when read. Restore the previous key, or set "
    "app.allow_secret_key_change to accept the new one and re-enter every "
    "stored credential."
)

UNMIGRATED = (
    "No secret_key_fingerprint table. Run the migrations "
    "(`alembic upgrade head`), then start the app."
)


def fingerprint(key):
    return hashlib.sha256(str(key).encode()).hexdigest()


def check_secret_key(engine, key, allow_change=False):
    """Refuse to start on a key the database's encrypted columns were not written under."""
    if not sa.inspect(engine).has_table(SecretKeyFingerprint.name):
        raise RuntimeError(UNMIGRATED)

    digest = fingerprint(key)
    with engine.begin() as connection:
        stored = connection.execute(
            sa.select(SecretKeyFingerprint.c.fingerprint).where(
                SecretKeyFingerprint.c.id == 1
            )
        ).scalar()

        if stored is None:
            # Workers start together, so whichever arrives first records it.
            connection.execute(
                pg_insert(SecretKeyFingerprint)
                .values(id=1, fingerprint=digest)
                .on_conflict_do_nothing()
            )
            return
        if stored == digest:
            return
        if not allow_change:
            raise RuntimeError(CHANGED)

        connection.execute(
            sa.update(SecretKeyFingerprint)
            .where(SecretKeyFingerprint.c.id == 1)
            .values(fingerprint=digest)
        )
    print("app.secret_key changed; recorded the new one", file=sys.stderr)
