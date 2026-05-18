"""Coordination primitives for running services as multiple replicas.

The helpers here let services in ``services/`` cooperate over PostgreSQL when
more than one replica is running, without introducing a new queue technology.

Three patterns are exposed:

- :func:`service_leader_lock` -- single-leader via a *transactional* advisory
  lock. Wrap a service's per-tick transaction so only one replica's tick
  actually does work. Auto-releases on commit/rollback. Use for periodic /
  cron-shaped services with a single transaction per tick.
- :func:`service_leader_session_lock` -- single-leader via a *session-level*
  advisory lock on a dedicated connection. Survives intermediate commits.
  Use when the tick body commits several times and ``service_leader_lock``
  would release the lock prematurely.
- :func:`claim_pending_rows` -- per-row claim via ``FOR UPDATE SKIP LOCKED``.
  Use for queue-shaped services where you want N replicas to truly split the
  workload.

Both rely only on PostgreSQL primitives. They are no-ops in single-replica
deploys (the leader lock is always acquired; ``SKIP LOCKED`` behaves like a
plain ``FOR UPDATE``).
"""

import zlib
from contextlib import contextmanager

import sqlalchemy as sa


def service_lock_key(name: str) -> int:
    """Stable 32-bit int key for a named service's advisory lock."""
    return zlib.crc32(name.encode("utf-8"))


@contextmanager
def service_leader_lock(session, name: str, blocking: bool = False):
    """Acquire a transactional advisory lock for the named service.

    Must be used inside an active transaction; the lock auto-releases on
    commit/rollback.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
    name : str
        Service identifier, e.g. ``"reminders"``. Same name across replicas.
    blocking : bool
        If False (default), yield True only if the lock was acquired now; yield
        False if another replica already holds it (so the caller skips the
        tick). If True, block until the lock is acquired.

    Yields
    ------
    bool
        Whether the lock is held by this caller.
    """
    key = service_lock_key(name)
    if blocking:
        session.execute(sa.text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})
        yield True
    else:
        got = session.execute(
            sa.text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": key}
        ).scalar()
        yield bool(got)


@contextmanager
def service_leader_session_lock(engine, name: str, blocking: bool = False):
    """Acquire a session-level (NOT transactional) advisory lock.

    Unlike :func:`service_leader_lock`, this one survives intermediate
    commits/rollbacks on other sessions. Use it to serialize services whose
    tick bodies commit several times (so ``pg_advisory_xact_lock`` would
    release prematurely). The lock is bound to a dedicated DB connection
    checked out of the pool for the lifetime of the context.

    Parameters
    ----------
    engine : sqlalchemy.engine.Engine
        Typically ``DBSession.get_bind()``.
    name : str
    blocking : bool

    Yields
    ------
    bool
        Whether the lock is held by this caller.
    """
    key = service_lock_key(name)
    conn = engine.connect()
    got = False
    try:
        if blocking:
            conn.execute(sa.text("SELECT pg_advisory_lock(:k)"), {"k": key})
            got = True
        else:
            got = bool(
                conn.execute(
                    sa.text("SELECT pg_try_advisory_lock(:k)"), {"k": key}
                ).scalar()
            )
        # Commit so the lock isn't held inside an idle-in-transaction state
        # that would block other writers on the same connection.
        conn.commit()
        yield got
    finally:
        try:
            if got:
                conn.execute(sa.text("SELECT pg_advisory_unlock(:k)"), {"k": key})
                conn.commit()
        finally:
            conn.close()


def claim_pending_rows(session, stmt, limit: int | None = None):
    """Claim rows for processing via ``SELECT ... FOR UPDATE SKIP LOCKED``.

    Concurrent replicas calling this with the same stmt receive disjoint row
    sets; the locks are held for the duration of the current transaction.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
    stmt : sqlalchemy.sql.Select
        Select statement identifying candidate rows. Must select rows of a
        single mapped class (so ``session.scalars`` returns ORM objects).
    limit : int, optional
        Cap on rows claimed per call. If None, claims all matching rows.

    Returns
    -------
    list
        ORM instances locked for this transaction.
    """
    stmt = stmt.with_for_update(skip_locked=True)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt).all())
