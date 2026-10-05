"""Where the key comes from, and why it is one place rather than three.

It is the AES key for credential columns every process shares, so a pod that
disagrees reads InvalidPaddingError and one that disagrees about cookies
fails websocket auth against its neighbour.
"""

import pytest

from skyportal.models import app_secret as module


@pytest.fixture(autouse=True)
def _forget():
    module.reset_secret_key()
    yield
    module.reset_secret_key()


def test_a_configured_key_wins(monkeypatch):
    # The operator owns it, and the database holds only a fingerprint -- a
    # stolen backup is then ciphertext without a key.
    monkeypatch.setitem(module.cfg["app"], "secret_key", "chosen-by-an-operator")
    monkeypatch.setattr(
        module, "_from_database", lambda: pytest.fail("should not have been asked")
    )
    assert module.secret_key() == "chosen-by-an-operator"


def test_the_shipped_default_is_not_a_choice(monkeypatch):
    # Running on the published key is the thing the guard exists to stop, so
    # it counts as unset and the database decides instead.
    monkeypatch.setitem(module.cfg["app"], "secret_key", module.DEFAULT_SECRET_KEY)
    monkeypatch.setattr(module, "_from_database", lambda: "from-the-database")
    assert module.secret_key() == "from-the-database"


def test_an_empty_key_falls_through_too(monkeypatch):
    monkeypatch.setitem(module.cfg["app"], "secret_key", "")
    monkeypatch.setattr(module, "_from_database", lambda: "from-the-database")
    assert module.secret_key() == "from-the-database"


def test_it_is_resolved_once(monkeypatch):
    # Every encrypt and decrypt calls this; it must not query each time.
    monkeypatch.setitem(module.cfg["app"], "secret_key", "")
    calls = []

    def once():
        calls.append(1)
        return "from-the-database"

    monkeypatch.setattr(module, "_from_database", once)
    assert module.secret_key() == module.secret_key() == "from-the-database"
    assert len(calls) == 1


def test_the_columns_ask_for_it_lazily():
    # The models are imported before init_db runs, so a key read at
    # class-definition time could never have come from the database.
    from skyportal.models.allocation import Allocation

    column = next(c for c in Allocation.__table__.c if c.name == "_altdata")
    assert callable(column.type._key)
    assert column.type._key is module.secret_key


def test_the_key_is_read_without_touching_the_shared_session():
    # The first bind of an encrypted column can happen inside another
    # transaction's flush; committing the shared session there ends that
    # transaction under its owner, which reads as "This transaction is closed"
    # somewhere unrelated.
    from unittest.mock import MagicMock, patch

    import baselayer.app.models as baselayer_models

    connection = MagicMock()
    connection.execute.return_value.scalar_one.return_value = "from-its-own-connection"
    engine = MagicMock()
    # A real Engine is its own .engine, which is how the unwrap reaches it.
    engine.engine = engine
    engine.connect.return_value.__enter__.return_value = connection

    with (
        patch.object(baselayer_models, "db_engine", return_value=engine),
        patch.object(baselayer_models, "DBSession") as shared_session,
    ):
        assert module._from_database() == "from-its-own-connection"

    shared_session.assert_not_called()
    connection.commit.assert_called_once()
