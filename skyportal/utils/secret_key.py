"""Supply app.secret_key to a container, and hold the database to one key.

The image bakes docker.yaml in as config.yaml, so every container built from
it would otherwise run on the key published in config.yaml.defaults, which is
the one the app refuses to start on. The generated key is kept in the
persistentdata volume, so sessions and the credentials encrypted under it
survive a restart; a fresh volume means a fresh key, and old sessions stop
working, which is the right trade for a key nobody chose. Pods sharing a
read-write-many volume settle on one key; give each its own volume and they
will not, so set app.secret_key yourself there.

The key also encrypts credential columns in the shared database, where a
mismatch surfaces as an InvalidPaddingError somewhere in a later request.
check_secret_key turns that into a refusal to start.
"""

import hashlib
import os
import pathlib
import re
import secrets
import sys

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from baselayer.app.models import Base

DEFAULT = "abc01234"
CONFIG = pathlib.Path("config.yaml")
STORE = pathlib.Path("persistentdata/secret_key")
SECRET_KEY_LINE = re.compile(r"^(\s*)secret_key:.*$", re.MULTILINE)


def current(text):
    match = SECRET_KEY_LINE.search(text)
    return match.group(0).split(":", 1)[1].strip() if match else None


def stored_key():
    """The key this volume has been given, generating it once if it has none.

    Created with O_EXCL so replicas sharing the volume settle on one key: the
    loser of the race reads the winner's rather than keeping its own. Workers
    inside a container never race -- this runs once, before the app starts --
    but websocket auth breaks across any two processes with different keys, so
    it is worth making the shared-volume case deterministic too.
    """
    STORE.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(STORE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w") as handle:
                handle.write(secrets.token_urlsafe(32) + "\n")
        if key := STORE.read_text().strip():
            return key
        # Created but not written: a crash in that window would otherwise
        # leave every later start reading an empty key.
        STORE.unlink(missing_ok=True)
    raise RuntimeError(f"could not settle on a secret key at {STORE}")


def ensure_secret_key():
    if not CONFIG.exists():
        return 0
    text = CONFIG.read_text()
    present = current(text)
    if present not in (None, "", DEFAULT):
        return 0  # someone set one; leave it alone

    key = stored_key()
    if present is not None:
        text = SECRET_KEY_LINE.sub(rf"\g<1>secret_key: {key}", text, count=1)
    elif re.search(r"^app:$", text, re.MULTILINE):
        text = re.sub(
            r"^app:$", f"app:\n  secret_key: {key}", text, count=1, flags=re.MULTILINE
        )
    else:
        # No app block to extend; start one rather than write nothing and
        # leave the app on the key it refuses to run with.
        text = text.rstrip("\n") + f"\n\napp:\n  secret_key: {key}\n"
    CONFIG.write_text(text)
    print("generated an app.secret_key for this container", file=sys.stderr)
    return 0


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
