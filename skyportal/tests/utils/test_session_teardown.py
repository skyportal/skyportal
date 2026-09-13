"""A request's session cleanup must not raise after the response is sent.

pgbouncer closes a connection that sat idle inside a transaction past
``idle_transaction_timeout``. The next request to reuse it fails its rollback in
``on_finish``, and because that runs after the response, the exception lands in
Tornado's error handling as "Exception in exception handler" -- obscuring the
real outcome of the request that happened to draw the dead connection.
"""

from sqlalchemy.exc import OperationalError

from baselayer.app.handlers.base import PSABaseHandler
from baselayer.app.models import DBSession


def _dead_connection_error():
    """What SQLAlchemy raises when the rollback finds the connection gone."""
    return OperationalError("ROLLBACK", {}, Exception("idle transaction timeout"))


def test_on_finish_survives_a_connection_the_server_already_closed(monkeypatch):
    cleared = []
    monkeypatch.setattr(
        DBSession, "remove", lambda: (_ for _ in ()).throw(_dead_connection_error())
    )
    monkeypatch.setattr(
        type(DBSession.registry), "clear", lambda self: cleared.append(True)
    )

    # on_finish touches no request state, so a bare object stands in for the
    # handler; what matters is that cleanup cannot propagate.
    PSABaseHandler.on_finish(object())

    assert cleared, "the unusable session was left in place for the next request"


def test_on_finish_still_removes_the_session_normally(monkeypatch):
    removed = []
    monkeypatch.setattr(DBSession, "remove", lambda: removed.append(True))
    cleared = []
    monkeypatch.setattr(
        type(DBSession.registry), "clear", lambda self: cleared.append(True)
    )

    PSABaseHandler.on_finish(object())

    assert removed, "the session was not removed on the normal path"
    assert not cleared, "the fallback ran when cleanup had in fact succeeded"


def test_on_finish_propagates_nothing_even_if_the_fallback_fails(monkeypatch):
    monkeypatch.setattr(
        DBSession, "remove", lambda: (_ for _ in ()).throw(_dead_connection_error())
    )
    monkeypatch.setattr(
        type(DBSession.registry),
        "clear",
        lambda self: (_ for _ in ()).throw(RuntimeError("registry is wedged")),
    )

    PSABaseHandler.on_finish(object())  # must still not raise
