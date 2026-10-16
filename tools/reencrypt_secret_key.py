"""Re-encrypt the columns keyed on app.secret_key after that key changes.

Several columns hold credentials encrypted with app.secret_key. Change the key
and the old ciphertext stops decrypting, which surfaces as
InvalidPaddingError and, for anything that lists brokers or allocations, an
empty page. This reads each row with the old key and writes it back with the
one now in the config.

Set app.secret_key to the new key before running this, since that is the key
the rows are written with; the old one is prompted for, or read from
OLD_SECRET_KEY, and goes nowhere near the config. In order: put the new key in config.yaml, stop the
instance, back the database up, run with --commit, start the instance.

A row written here cannot be recovered with the old key afterwards, which is
what the backup is for.

Anything encrypted under the key shipped in config.yaml.defaults was readable
by anyone holding the source, so prefer replacing those credentials at their
origin over carrying them across.

Run it from the repository root, where baselayer and skyportal are importable:

    make reencrypt_secret_key
    make reencrypt_secret_key FLAGS=--commit

or directly, naming the config the instance runs on, since without --config
only the .defaults are read and the key compared is the one they ship:

    PYTHONPATH=. python tools/reencrypt_secret_key.py \
        --config=config.yaml
"""

import getpass
import hashlib
import os
import sys

import sqlalchemy as sa
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    AesEngine,
    StringEncryptedType,
)

from baselayer.app.env import load_env, parser
from baselayer.log import make_log

log = make_log("reencrypt_secret_key")

parser.add_argument(
    "--commit", action="store_true", help="write the rows; otherwise report only"
)
env, cfg = load_env()


def fingerprint(key):
    """Names a key in the log without disclosing it."""
    if key is None:
        return "absent"
    digest = hashlib.sha256(str(key).encode()).hexdigest()[:8]
    return f"{digest} ({len(str(key))} chars)"


def engine_for(key):
    """An engine configured as StringEncryptedType configures its own."""
    engine = AesEngine()
    engine._set_padding_mechanism("pkcs5")
    engine._update_key(key)
    return engine


def encrypted_columns():
    """Every encrypted column, found rather than listed, so one added later is
    covered without editing this."""
    from skyportal.models import Base

    return [
        (table, column)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, StringEncryptedType)
    ]


def rekey(connection, table, column, old, new, commit):
    """Returns (rows seen, to re-encrypt, already on the new key, unreadable).

    The ciphertext is read and written through typeless columns: going through
    the mapped ones would decrypt on the way out, with the key that cannot read
    these rows, and encrypt a second time on the way in.
    """
    pk_name = list(table.primary_key.columns)[0].name
    raw = sa.table(
        table.name, sa.column(pk_name), sa.column(column.name), schema=table.schema
    )
    raw_pk, raw_col = raw.c[pk_name], raw.c[column.name]
    rows = connection.execute(
        sa.select(raw_pk, raw_col).where(raw_col.isnot(None))
    ).fetchall()

    total = len(rows)
    moved, already, unreadable = 0, 0, []
    for key_value, ciphertext in rows:
        try:
            new.decrypt(ciphertext)
            already += 1
            continue
        except Exception:
            pass
        try:
            plaintext = old.decrypt(ciphertext)
        except Exception:
            unreadable.append(key_value)
            continue
        if commit:
            connection.execute(
                sa.update(raw)
                .where(raw_pk == key_value)
                .values({column.name: new.encrypt(plaintext)})
            )
        moved += 1
    return total, moved, already, unreadable


def main():
    old_key = os.environ.get("OLD_SECRET_KEY") or getpass.getpass(
        "Previous app.secret_key: "
    )
    new_key = cfg["app.secret_key"]
    log(f"config files given with --config: {', '.join(env.config or ()) or 'none'}")
    if not env.config:
        log(
            "Only the .defaults were loaded, so app.secret_key below is the one "
            "they ship. Pass --config=config.yaml, the same file the instance "
            "runs on, or the keys compared here are not the keys in use."
        )
    log(f"app.secret_key in the config: {fingerprint(new_key)}")
    log(f"previous key: {fingerprint(old_key)}")
    log(f"mode: {'commit, rows will be written' if env.commit else 'report only'}")

    if new_key is None:
        log(
            "app.secret_key is absent from the config. It belongs under the app: "
            "section, so the tool reads it as the path app.secret_key."
        )
        return 1
    if not old_key:
        log("No previous key given.")
        return 1
    if old_key == new_key:
        log(
            "The previous key matches app.secret_key in the config, so there is "
            "nothing to move. Put the new key in the config first."
        )
        return 0

    old, new = engine_for(old_key), engine_for(new_key)
    columns = encrypted_columns()
    if not columns:
        log("No encrypted columns found; is this a skyportal database?")
        return 1
    log(
        f"{len(columns)} encrypted column(s): "
        + ", ".join(f"{t.name}.{c.name}" for t, c in columns)
    )

    from skyportal.models import init_db

    log(f"database: {cfg['database.database']}")
    totals = {"rows": 0, "moved": 0, "already": 0, "unreadable": 0}
    with init_db(**cfg["database"]).connect() as connection:
        for table, column in columns:
            total, moved, already, unreadable = rekey(
                connection, table, column, old, new, env.commit
            )
            totals["rows"] += total
            totals["moved"] += moved
            totals["already"] += already
            totals["unreadable"] += len(unreadable)
            log(
                f"{table.name}.{column.name}: {total} row(s) with a value, "
                f"{moved} to re-encrypt, {already} already on the new key, "
                f"{len(unreadable)} unreadable"
            )
            if unreadable:
                log(f"  unreadable rows: {sorted(unreadable)}")
        if env.commit:
            connection.commit()

    if totals["rows"] == 0:
        log(
            "No encrypted values anywhere in this database, so there is nothing "
            "to move; check this is the database the instance uses."
        )
    if totals["unreadable"]:
        log(
            f"{totals['unreadable']} row(s) decrypt with neither key; they were "
            "written under some third key and have to be re-entered."
        )
    if env.commit:
        log(f"Re-encrypted {totals['moved']} row(s).")
    else:
        log(
            f"Would re-encrypt {totals['moved']} row(s). "
            "Re-run with --commit once the database is backed up."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
