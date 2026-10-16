"""Re-encrypt the columns keyed on app.secret_key after that key changes.

Several columns hold credentials encrypted with app.secret_key. Change the key
and the old ciphertext stops decrypting, which surfaces as
InvalidPaddingError and, for anything that lists brokers or allocations, an
empty page. This reads each row with the old key and writes it back with the
one now in the config.

The instance has to be stopped while this runs, and the database backed up
first: a row written here cannot be recovered with the old key afterwards.

Anything encrypted under the key shipped in config.yaml.defaults was readable
by anyone holding the source, so prefer replacing those credentials at their
origin over carrying them across.

    python tools/reencrypt_secret_key.py --old-key abc01234
    python tools/reencrypt_secret_key.py --old-key abc01234 --commit
"""

import sys

import sqlalchemy as sa
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    AesEngine,
    StringEncryptedType,
)

from baselayer.app.env import load_env, parser
from baselayer.log import make_log

log = make_log("reencrypt_secret_key")

parser.add_argument("--old-key", required=True, help="the previous app.secret_key")
parser.add_argument(
    "--commit", action="store_true", help="write the rows; otherwise report only"
)
env, cfg = load_env()


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
    """Returns (moved, already, unreadable) for one column.

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
    return moved, already, unreadable


def main():
    new_key = cfg["app.secret_key"]
    if env.old_key == new_key:
        log("--old-key is the key already in the config; nothing to do.")
        return 0

    old, new = engine_for(env.old_key), engine_for(new_key)
    columns = encrypted_columns()
    if not columns:
        log("No encrypted columns found; is this a skyportal database?")
        return 1

    from skyportal.models import init_db

    totals = {"moved": 0, "already": 0, "unreadable": 0}
    # connect() rather than begin(), so the dry run ends in a rollback the
    # context manager will not try to commit over.
    with init_db(**cfg["database"]).connect() as connection:
        for table, column in columns:
            moved, already, unreadable = rekey(
                connection, table, column, old, new, env.commit
            )
            totals["moved"] += moved
            totals["already"] += already
            totals["unreadable"] += len(unreadable)
            log(
                f"{table.name}.{column.name}: {moved} to re-encrypt, "
                f"{already} already on the new key, {len(unreadable)} unreadable"
            )
            if unreadable:
                log(f"  unreadable rows: {sorted(unreadable)}")
        if env.commit:
            connection.commit()
        else:
            connection.rollback()

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
