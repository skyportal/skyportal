"""Enable pgvector in the databases, which the summary embeddings table needs.

Installing an extension is a superuser act, so it happens here beside database
creation rather than from the application role while the app is running. Which
role is the superuser varies: a container usually makes the application's own
one, while a local install has it apart, so both are tried.
"""

import os
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

flags = ["--no-password"]
if cfg["database.host"]:
    flags += ["-h", str(cfg["database.host"])]
if cfg["database.port"]:
    flags += ["-p", str(cfg["database.port"])]

psql_env = dict(os.environ)
if cfg["database.password"]:
    psql_env["PGPASSWORD"] = cfg["database.password"]

users = [cfg["database.user"] or db, cfg.get("database.admin_user") or "postgres"]


def psql(user, statement, database):
    return subprocess.run(
        ["psql", *flags, "-U", user, "-c", statement, database],
        capture_output=True,
        env=psql_env,
    )


for database in databases:
    # A database that cannot be reached at all is one this install does not use;
    # db_init leaves such a database alone too.
    if not any(psql(user, "SELECT 1;", database).returncode == 0 for user in users):
        continue

    for user in users:
        p = psql(user, "CREATE EXTENSION IF NOT EXISTS vector;", database)
        if p.returncode == 0:
            log(f"pgvector enabled in {database}")
            break
    else:
        log(f"Could not enable pgvector in {database}:")
        log(p.stderr.decode("utf-8").strip())
        log("The summary embeddings table cannot be created until it is there.")
        sys.exit(1)
