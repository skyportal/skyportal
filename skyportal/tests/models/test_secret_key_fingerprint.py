"""The app refuses to start on a secret key the database was not last started on.

The key encrypts credential columns, so a change that goes unnoticed leaves
those rows raising InvalidPaddingError wherever they are next read.
"""

import pytest
import sqlalchemy as sa
import yaml

from skyportal.models.secret_key_fingerprint import (
    SecretKeyFingerprint,
    check_secret_key,
    fingerprint,
)


@pytest.fixture()
def engine():
    cfg = yaml.safe_load(open("test_config.yaml")).get("database", {})
    url = sa.engine.URL.create(
        "postgresql+psycopg",
        username=cfg.get("user", "skyportal"),
        password=cfg.get("password") or None,
        host=cfg.get("host", "localhost"),
        port=cfg.get("port", 5432),
        database=cfg.get("database", "skyportal_test"),
    )
    engine = sa.create_engine(url)
    try:
        engine.connect().close()
    except sa.exc.OperationalError as exc:
        pytest.skip(f"no test database: {exc}")
    SecretKeyFingerprint.create(engine, checkfirst=True)
    with engine.begin() as connection:
        connection.execute(sa.delete(SecretKeyFingerprint))
    yield engine
    engine.dispose()


def stored(engine):
    with engine.begin() as connection:
        return connection.execute(
            sa.select(SecretKeyFingerprint.c.fingerprint)
        ).scalar()


def test_the_first_start_records_the_key(engine):
    check_secret_key(engine, "first-key")
    assert stored(engine) == fingerprint("first-key")


def test_the_same_key_starts_again(engine):
    check_secret_key(engine, "first-key")
    check_secret_key(engine, "first-key")
    assert stored(engine) == fingerprint("first-key")


def test_the_key_is_not_stored_in_the_clear(engine):
    check_secret_key(engine, "first-key")
    assert "first-key" not in stored(engine)


def test_a_different_key_refuses_to_start(engine):
    check_secret_key(engine, "first-key")
    with pytest.raises(RuntimeError, match="credentials"):
        check_secret_key(engine, "second-key")
    assert stored(engine) == fingerprint("first-key")


def test_allow_secret_key_change_accepts_the_new_key(engine):
    check_secret_key(engine, "first-key")
    check_secret_key(engine, "second-key", allow_change=True)
    assert stored(engine) == fingerprint("second-key")


def test_an_unmigrated_database_says_to_migrate(engine):
    SecretKeyFingerprint.drop(engine)
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        check_secret_key(engine, "first-key")
    SecretKeyFingerprint.create(engine)
