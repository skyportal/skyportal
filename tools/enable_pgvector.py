"""Enable pgvector in the databases, which the summary embeddings table needs.

Installing an extension takes a superuser, and which role that is varies, so
every candidate is tried.
"""

import os
import shutil
import subprocess
import sys

from baselayer.app.env import load_env, parser
from baselayer.log import make_log

log = make_log("enable_pgvector")

parser.add_argument(
    "--test-only", action="store_true", help="only act on the test database"
)
env, cfg = load_env()

db = cfg["database.database"]
databases = (f"{db}_test",) if env.test_only else (db, f"{db}_test")

port = ["-p", str(cfg["database.port"])] if cfg["database.port"] else []
flags = ["--no-password", *port]
if cfg["database.host"]:
    flags += ["-h", str(cfg["database.host"])]

psql_env = dict(os.environ)
if cfg["database.password"]:
    psql_env["PGPASSWORD"] = cfg["database.password"]

admin_user = cfg.get("database.admin_user") or "postgres"
clients = [
    ["psql", *flags, "-U", cfg["database.user"] or db],
    ["psql", *flags, "-U", admin_user],
]
# Stock Linux installs only admit the superuser through peer auth on the socket;
# `-n` relies on credentials that `db_init` cached, and never prompts.
if shutil.which("sudo"):
    clients.append(
        ["sudo", "-n", "-u", admin_user, "psql", "-X", "--no-password", *port]
    )


def psql(client, statement, database):
    return subprocess.run(
        [*client, "-t", "-A", "-c", statement, database],
        capture_output=True,
        env=psql_env,
    )


for database in databases:
    reachable = [c for c in clients if psql(c, "SELECT 1;", database).returncode == 0]
    # A database that cannot be reached is one this install does not use.
    if not reachable:
        continue

    p = psql(
        reachable[0],
        "SELECT 1 FROM pg_available_extensions WHERE name = 'vector';",
        database,
    )
    if p.returncode == 0 and not p.stdout.strip():
        log("pgvector is not installed on the PostgreSQL server. Install it with:")
        log("  Fedora/RHEL:   sudo dnf install pgvector")
        log("  Debian/Ubuntu: sudo apt install postgresql-<version>-pgvector")
        log("  macOS:         brew install pgvector")
        sys.exit(1)

    errors = []
    for client in reachable:
        p = psql(client, "CREATE EXTENSION IF NOT EXISTS vector;", database)
        if p.returncode == 0:
            via = f" (with `{' '.join(client[:4])}`)" if client[0] == "sudo" else ""
            log(f"pgvector enabled in {database}{via}")
            break
        errors.append(p.stderr.decode("utf-8").strip())
    else:
        log(f"Could not enable pgvector in {database}:")
        for error in errors:
            log(error)
        log("Create it as a superuser with:")
        log(f"  sudo -u {admin_user} psql -c 'CREATE EXTENSION vector;' {database}")
        log("The summary embeddings table cannot be created until it is there.")
        sys.exit(1)
