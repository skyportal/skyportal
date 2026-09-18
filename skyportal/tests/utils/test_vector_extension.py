"""What `ensure_vector_extension` tells you when it cannot install pgvector.

A server without the extension and a role that may not install one need
different fixes, so the two must not share a message.
"""

import types

import pytest

from skyportal.models.summary_embedding import ensure_vector_extension


class FakeConnection:
    """Answers the two catalogue lookups, and may refuse the CREATE."""

    def __init__(self, installed=False, available=True, may_install=True):
        self.installed = installed
        self.available = available
        self.may_install = may_install
        self.created = False
        self.engine = types.SimpleNamespace(
            url=types.SimpleNamespace(database="skyportal")
        )

    def scalar(self, statement):
        sql = str(statement)
        if "pg_extension" in sql:
            return 1 if self.installed else None
        if "pg_available_extensions" in sql:
            return 1 if self.available else None
        raise AssertionError(f"unexpected query: {sql}")

    def execute(self, statement):
        if not self.may_install:
            raise PermissionError("permission denied to create extension vector")
        self.created = True


def test_an_installed_extension_is_left_alone():
    connection = FakeConnection(installed=True)
    ensure_vector_extension(connection)
    assert not connection.created


def test_it_is_created_when_absent_and_permitted():
    connection = FakeConnection()
    ensure_vector_extension(connection)
    assert connection.created


def test_a_server_without_pgvector_is_told_to_install_it():
    connection = FakeConnection(available=False)
    with pytest.raises(RuntimeError, match="pgvector/pgvector"):
        ensure_vector_extension(connection)
    # No point attempting a CREATE the server cannot satisfy.
    assert not connection.created


def test_an_unprivileged_role_is_told_to_ask_an_administrator():
    connection = FakeConnection(may_install=False)
    with pytest.raises(RuntimeError, match="may not install extensions") as caught:
        ensure_vector_extension(connection)
    assert isinstance(caught.value.__cause__, PermissionError)


def test_the_database_is_named_in_both_messages():
    for connection in (
        FakeConnection(available=False),
        FakeConnection(may_install=False),
    ):
        with pytest.raises(RuntimeError, match="skyportal"):
            ensure_vector_extension(connection)
