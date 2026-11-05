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
# Stock Linux installs only admit the superuser through peer auth on the socket.
sudo_client = ["sudo", "-n", "-u", admin_user, "psql", "-X", "--no-password", *port]
use_sudo = None


def psql(client, statement, database):
    return subprocess.run(
        [*client, "-t", "-A", "-c", statement, database],
        capture_output=True,
        env=psql_env,
    )


def ask_sudo(command):
    """Ask once whether to run sudo; the alternative is to run `command` by hand."""
    global use_sudo
    if use_sudo is None:
        use_sudo = False
        if sys.stdin.isatty() and shutil.which("sudo"):
            print(
                "\nEnabling pgvector needs a superuser. Either:\n\n"
                f"  1. Let this script run `sudo -u {admin_user} psql`. "
                "sudo can ask for your password.\n"
                "  2. Answer no, and run this command yourself:\n\n"
                f"       {command}\n"
            )
            try:
                answer = input("Use sudo? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            use_sudo = answer in ("y", "yes") and (
                subprocess.run(["sudo", "-v"]).returncode == 0
            )
    return use_sudo


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

    statement = "CREATE EXTENSION IF NOT EXISTS vector;"
    command = f"sudo -u {admin_user} psql -c '{statement}' {database}"
    errors = []
    for client in reachable:
        p = psql(client, statement, database)
        if p.returncode == 0:
            log(f"pgvector enabled in {database}")
            break
        errors.append(p.stderr.decode("utf-8").strip())
    else:
        if ask_sudo(command):
            p = psql(sudo_client, statement, database)
            if p.returncode == 0:
                log(f"pgvector enabled in {database} (with `sudo -u {admin_user}`)")
                continue
            errors.append(p.stderr.decode("utf-8").strip())
        log(f"Could not enable pgvector in {database}:")
        for error in errors:
            log(error)
        log("Run this command yourself, then run this script again:")
        log(f"  {command}")
        log("The summary embeddings table cannot be created until it is there.")
        sys.exit(1)
