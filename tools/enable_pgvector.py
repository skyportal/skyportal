"""Enable pgvector in the databases, which the summary embeddings table needs.

Installing an extension is a superuser act, so it happens here beside database
creation rather than from the application role while the app is running. Which
role is the superuser varies: a container usually makes the application's own
one, while a local install has it apart, so both are tried.
"""

import subprocess

from baselayer.app.env import load_env, parser
from baselayer.log import make_log

log = make_log("enable_pgvector")

parser.add_argument(
    "--test-only", action="store_true", help="only act on the test database"
)
env, cfg = load_env()

db = cfg["database.database"]
databases = (f"{db}_test",) if env.test_only else (db, f"{db}_test")

psql_cmd = "psql"
if cfg["database.password"]:
    psql_cmd = f'PGPASSWORD="{cfg["database.password"]}" {psql_cmd}'
flags = "--no-password"
if cfg["database.host"]:
    flags += f" -h {cfg['database.host']}"
if cfg["database.port"]:
    flags += f" -p {cfg['database.port']}"

users = [cfg["database.user"] or db, cfg.get("database.admin_user") or "postgres"]

for database in databases:
    for user in users:
        p = subprocess.run(
            f"{psql_cmd} {flags} -U {user} "
            f'-c "CREATE EXTENSION IF NOT EXISTS vector;" {database}',
            capture_output=True,
            shell=True,
        )
        if p.returncode == 0:
            log(f"pgvector enabled in {database}")
            break
    else:
        log(f"Could not enable pgvector in {database}:")
        log(p.stderr.decode("utf-8").strip())
        log("The summary embeddings table cannot be created until it is there.")
