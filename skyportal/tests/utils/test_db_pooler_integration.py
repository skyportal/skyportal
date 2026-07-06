"""End-to-end connection-pooling tests: run a real pgbouncer in front of the
test Postgres and verify SkyPortal routes through it (sync + async) and that
many clients multiplex onto a small bounded backend pool.

Skipped unless the ``pgbouncer`` binary is installed (see the CI install step).
"""

import asyncio
import shutil
import socket
import subprocess
import threading
import time

import psycopg
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from baselayer.app.config import load_config
from baselayer.app.models import _resolve_pooler

pytestmark = pytest.mark.skipif(
    shutil.which("pgbouncer") is None, reason="pgbouncer not installed"
)

DB = load_config()["database"]
POOL_SIZE = 2


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _url(host, port):
    return (
        f"postgresql+psycopg://{DB['user']}:{DB.get('password') or ''}"
        f"@{host}:{port}/{DB['database']}"
    )


@pytest.fixture
def pgbouncer(tmp_path):
    """A transaction-mode pgbouncer in front of the test Postgres."""
    port = _free_port()
    password = DB.get("password") or ""
    # Client->pgbouncer uses trust (test-only, robust with or without a password);
    # pgbouncer->Postgres uses the real password from the [databases] entry.
    (tmp_path / "userlist.txt").write_text(f'"{DB["user"]}" ""\n')
    backend = (
        f"host={DB['host'] or 'localhost'} port={DB['port'] or 5432} "
        f"dbname={DB['database']} user={DB['user']}"
        + (f" password={password}" if password else "")
    )
    (tmp_path / "pgbouncer.ini").write_text(
        f"""
[databases]
{DB["database"]} = {backend}
[pgbouncer]
listen_addr = 127.0.0.1
listen_port = {port}
pool_mode = transaction
default_pool_size = {POOL_SIZE}
max_client_conn = 200
auth_type = trust
auth_file = {tmp_path / "userlist.txt"}
admin_users = {DB["user"]}
ignore_startup_parameters = extra_float_digits, options
logfile = {tmp_path / "pgbouncer.log"}
pidfile = {tmp_path / "pgbouncer.pid"}
"""
    )
    proc = subprocess.Popen(["pgbouncer", str(tmp_path / "pgbouncer.ini")])
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("pgbouncer did not start listening")
    try:
        yield port
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _pooled_engine(port):
    host, port, engine_args = _resolve_pooler(
        DB["host"],
        DB["port"],
        {},
        {"enabled": True, "host": "127.0.0.1", "port": port},
    )
    return sa.create_engine(_url(host, port), **engine_args)


def test_sync_query_routes_through_pooler(pgbouncer):
    engine = _pooled_engine(pgbouncer)
    try:
        assert engine.url.port == pgbouncer
        with engine.connect() as conn:
            assert conn.execute(sa.text("SELECT 1")).scalar() == 1
    finally:
        engine.dispose()


def test_async_query_routes_through_pooler(pgbouncer):
    host, port, engine_args = _resolve_pooler(
        DB["host"],
        DB["port"],
        {},
        {"enabled": True, "host": "127.0.0.1", "port": pgbouncer},
    )
    engine = create_async_engine(_url(host, port), **engine_args)

    async def run():
        async with engine.connect() as conn:
            value = (await conn.execute(sa.text("SELECT 2"))).scalar()
        await engine.dispose()
        return value

    assert asyncio.run(run()) == 2


def _show_pools(port):
    """Return pgbouncer's SHOW POOLS row for the test database."""
    with psycopg.connect(
        host="127.0.0.1",
        port=port,
        dbname="pgbouncer",
        user=DB["user"],
        password=DB.get("password") or "",
        autocommit=True,
        prepare_threshold=None,
    ) as admin:
        cur = admin.execute("SHOW POOLS")
        cols = [c.name for c in cur.description]
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            if d["database"] == DB["database"]:
                return d
    return None


def test_many_clients_multiplex_onto_small_backend_pool(pgbouncer):
    """More concurrent clients than the pool size are all served, while backend
    connections stay bounded at pool_size (the mechanism that prevents Postgres
    max_connections exhaustion)."""
    n_clients = POOL_SIZE + 6
    ok = []
    ok_lock = threading.Lock()
    barrier = threading.Barrier(n_clients + 1)
    peak = {"servers": 0, "clients": 0}

    def client():
        barrier.wait()
        try:
            with psycopg.connect(
                host="127.0.0.1",
                port=pgbouncer,
                dbname=DB["database"],
                user=DB["user"],
                password=DB.get("password") or "",
                prepare_threshold=None,
            ) as conn:
                conn.execute("SELECT pg_sleep(0.6)")
            with ok_lock:
                ok.append(True)
        except Exception:
            with ok_lock:
                ok.append(False)

    threads = [threading.Thread(target=client) for _ in range(n_clients)]
    for t in threads:
        t.start()
    barrier.wait()  # release all clients together
    # sample pgbouncer accounting while transactions are held
    for _ in range(40):
        pool = _show_pools(pgbouncer)
        if pool:
            peak["servers"] = max(
                peak["servers"], pool["sv_active"] + pool["sv_idle"] + pool["sv_used"]
            )
            peak["clients"] = max(
                peak["clients"], pool["cl_active"] + pool["cl_waiting"]
            )
        time.sleep(0.02)
    for t in threads:
        t.join()

    assert all(ok) and len(ok) == n_clients  # every client served, none rejected
    assert peak["clients"] > POOL_SIZE  # more clients than the pool at once
    assert peak["servers"] <= POOL_SIZE  # ... yet backend connections stay bounded
