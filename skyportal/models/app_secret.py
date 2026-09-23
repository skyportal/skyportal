"""Where app.secret_key comes from, and the one place it is decided.

It is the AES key for the credential columns in allocations, analyses,
brokers and sharing services, so every process touching those rows has to
agree on it: a pod that disagrees reads InvalidPaddingError, and one that
disagrees about session cookies fails websocket auth against its neighbour.

An operator who sets a key in the config owns it, and the database records
only a fingerprint -- a stolen backup then yields ciphertext and no key,
which is the reason those columns are encrypted at all. Where no key is set
the database holds the key itself: there is nothing to protect that the
database does not already contain, and the alternatives are a published
default or a key per pod.

Resolution is lazy because it has to be. `StringEncryptedType` accepts a
callable and re-reads it on every bind, and the models that use it are
imported before `init_db` runs, so a key read at class-definition time could
not come from the database.
"""

__all__ = ["SecretKey", "DEFAULT_SECRET_KEY", "secret_key", "reset_secret_key"]

import secrets

import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import Base, DBSession

env, cfg = load_env()

# The key shipped in config.yaml.defaults, which no deployment should run on.
DEFAULT_SECRET_KEY = "abc01234"

# One row: the key this database's encrypted columns were written under.
SecretKey = sa.Table(
    "secret_key",
    Base.metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
    sa.Column("key", sa.Text, nullable=False),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
    sa.CheckConstraint("id = 1", name="secret_key_singleton"),
)

_resolved = None


def reset_secret_key():
    """Forget the resolved key. For tests; nothing else should need it."""
    global _resolved
    _resolved = None


def _from_database():
    """The key this database already holds, generating one if it holds none.

    Inserted with ON CONFLICT DO NOTHING and then read back, so pods racing
    each other on a first start settle on whichever insert won rather than
    each keeping its own.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    session = DBSession()
    session.execute(
        pg_insert(SecretKey)
        .values(id=1, key=secrets.token_urlsafe(32))
        .on_conflict_do_nothing(index_elements=["id"])
    )
    session.commit()
    return session.execute(sa.select(SecretKey.c.key)).scalar_one()


def secret_key():
    """The key in force, resolved once.

    The config wins where it names one. Otherwise the database decides, which
    is what lets replicas agree without sharing a volume.
    """
    global _resolved
    if _resolved is None:
        configured = cfg.get("app.secret_key")
        if configured and configured != DEFAULT_SECRET_KEY:
            _resolved = configured
        else:
            _resolved = _from_database()
    return _resolved
