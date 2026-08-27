"""Report which revision a database's schema actually corresponds to.

`alembic current` reports what the alembic_version table was last set to, which
is not evidence that the migrations ran. `alembic stamp` sets that table without
touching the schema, so a database that was stamped while it was behind will
claim to be up to date, `make db_migrate` will have nothing left to do, and the
app will fail on the columns and tables the skipped migrations were meant to
add.

This reads the schema, compares it against the tables and columns each migration
creates, and reports the newest revision whose changes are all present. With
--stamp it sets alembic_version back to that revision, after which
`make db_migrate` replays the ones that were missed.
"""

import argparse
import ast
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__, add_help=True)
parser.add_argument(
    "--stamp",
    action="store_true",
    help="Set alembic_version to the revision the schema matches",
)
parser.add_argument(
    "--yes", action="store_true", help="Do not ask for confirmation when stamping"
)
parser.add_argument(
    "--verbose", action="store_true", help="Show the evidence for each revision"
)
args, _ = parser.parse_known_args()

import sqlalchemy as sa  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402

from baselayer.app.env import load_env  # noqa: E402
from baselayer.app.models import init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def dotted_name(node):
    """``op.add_column`` for the function of a call, or None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def literal(node):
    """The value of a literal argument, or None if it is computed."""
    try:
        return ast.literal_eval(node)
    except ValueError:
        return None


def column_names(call):
    """Names of the sa.Column(...) built anywhere inside a call."""
    names = []
    for node in ast.walk(call):
        if isinstance(node, ast.Call) and dotted_name(node.func) in (
            "sa.Column",
            "Column",
        ):
            if node.args:
                names.append(literal(node.args[0]))
    return [name for name in names if name]


def upgrade_ops(path):
    """The schema changes ``upgrade()`` makes, as far as they can be read.

    Only the operations that create or remove a table or column matter here.
    Anything else, including changes made through op.execute, leaves no marker
    and simply gives this revision no say.
    """
    tree = ast.parse(Path(path).read_text())
    upgrade = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
        ),
        None,
    )
    if upgrade is None:
        return []

    ops = []
    for node in ast.walk(upgrade):
        if not isinstance(node, ast.Call):
            continue
        name = dotted_name(node.func)
        arg = [literal(a) for a in node.args]

        if name == "op.create_table" and arg and arg[0]:
            ops.append(("create_table", arg[0], column_names(node)))
        elif name == "op.drop_table" and arg and arg[0]:
            ops.append(("drop_table", arg[0], None))
        elif name == "op.add_column" and len(arg) >= 1 and arg[0]:
            for column in column_names(node):
                ops.append(("add_column", arg[0], column))
        elif name == "op.drop_column" and len(arg) >= 2 and arg[0] and arg[1]:
            ops.append(("drop_column", arg[0], arg[1]))
        elif name == "op.rename_table" and len(arg) >= 2 and arg[0] and arg[1]:
            ops.append(("rename_table", arg[0], arg[1]))
        elif name == "op.alter_column" and len(arg) >= 2 and arg[0] and arg[1]:
            renamed = next(
                (
                    literal(kw.value)
                    for kw in node.keywords
                    if kw.arg == "new_column_name"
                ),
                None,
            )
            if renamed:
                ops.append(("rename_column", arg[0], (arg[1], renamed)))
    return ops


def replay(revisions):
    """Walk the history, recording what each revision creates.

    A revision's markers are the tables and columns it adds that are still there
    at the head, since those are the ones whose presence in a database says the
    revision ran. Anything a later revision removes or renames is dropped, so it
    cannot be mistaken for a revision that never ran.
    """
    schema = {}
    created = {}

    for revision, path in revisions:
        created[revision] = set()
        for kind, table, detail in upgrade_ops(path):
            if kind == "create_table":
                schema[table] = set(detail)
                created[revision].add((table, None))
                created[revision].update((table, column) for column in detail)
            elif kind == "drop_table":
                schema.pop(table, None)
            elif kind == "add_column":
                schema.setdefault(table, set()).add(detail)
                created[revision].add((table, detail))
            elif kind == "drop_column":
                schema.get(table, set()).discard(detail)
            elif kind == "rename_table":
                schema[detail] = schema.pop(table, set())
            elif kind == "rename_column":
                old, new = detail
                if old in schema.get(table, set()):
                    schema[table].discard(old)
                    schema[table].add(new)

    surviving = {(table, None) for table in schema}
    surviving |= {
        (table, column) for table, columns in schema.items() for column in columns
    }
    return {revision: markers & surviving for revision, markers in created.items()}


def read_schema(connection):
    rows = connection.execute(
        sa.text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public'"
        )
    ).all()
    present = {(table, None) for table, _ in rows}
    present |= {(table, column) for table, column in rows}
    return present


def name_markers(markers, limit=3):
    """``table.column`` for a few markers, table names alone for whole tables."""
    # a marker is (table, None) for a table and (table, column) for a column,
    # so it cannot be sorted without a key
    sample = sorted(markers, key=lambda m: (m[0], m[1] or ""))[:limit]
    named = ", ".join(
        table if column is None else f"{table}.{column}" for table, column in sample
    )
    return named + (", ..." if len(markers) > limit else "")


def report_collisions(order, verdict, markers, present, best):
    """Warn about pending revisions whose changes the database already has.

    A migration that has not run should leave no trace, so one that does will
    fail when it is replayed. This happens where a table arrives from the models
    rather than from its migration, which the app does for missing tables when
    it runs in debug mode: the table is built to the current model, while older
    tables never gain the columns their migrations would have added.
    """
    collisions = [
        (order[i], markers[order[i]] & present)
        for i in range(best + 1, len(order))
        if verdict[i] is True
    ]
    if not collisions:
        return

    print(
        f"{len(collisions)} of those migrations are already present in part, so the "
        "upgrade will\nstop at the first one it cannot apply:\n"
    )
    for revision, already in collisions:
        print(f"    {revision}  {name_markers(already)} already exists")
    print(
        "\nCheck each one, and if its changes really are all there, stamp past it\n"
        "with `alembic stamp <revision>` before continuing the upgrade.\n"
    )


def main():
    env, cfg = load_env()
    engine = init_db(**{**cfg["database"], "pooler": None})
    # the configuration decides this, so say which database was read
    print(f"Database: {cfg['database']['database']} on {cfg['database']['host']}\n")

    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    history = [
        (revision.revision, revision.path)
        for revision in script.walk_revisions("base", "heads")
    ]
    history.reverse()
    markers = replay(history)

    with engine.connect() as connection:
        present = read_schema(connection)
        if ("alembic_version", None) in present:
            recorded = (
                connection.execute(sa.text("SELECT version_num FROM alembic_version"))
                .scalars()
                .all()
            )
        else:
            recorded = []

    if len(recorded) > 1:
        print(f"alembic_version holds more than one revision: {', '.join(recorded)}")

    # A revision with no surviving markers leaves no trace to look for, so it
    # neither confirms nor denies anything.
    verdicts = []
    for revision, expected in ((r, markers[r]) for r, _ in history):
        if not expected:
            verdicts.append((revision, None, set()))
            continue
        missing = expected - present
        verdicts.append((revision, not missing, missing))

    if args.verbose:
        for revision, applied, missing in verdicts:
            state = {True: "present", False: "MISSING", None: "no evidence"}[applied]
            detail = f"  {name_markers(missing)}" if missing else ""
            print(f"  {revision}  {state}{detail}")

    order = [revision for revision, _ in history]
    verdict = [applied for _, applied, _ in verdicts]

    if not any(applied is not None for applied in verdict):
        print("No revision leaves a mark this can look for; nothing to compare.")
        return 0

    # A database sits at one point in the history, so the evidence should read
    # as applied up to somewhere and unapplied after it. Rather than trusting
    # any single revision, take the split that disagrees with the fewest of
    # them: a migration that removed a column through op.execute, or a column
    # the models create anyway, would otherwise be enough to reject the lot.
    # Ties go to the earliest split, since replaying a migration that already
    # ran fails loudly, while skipping one is the silent failure being repaired.
    unapplied_before = [0]
    for applied in verdict:
        unapplied_before.append(unapplied_before[-1] + (applied is False))
    applied_total = sum(applied is True for applied in verdict)

    best, fewest = -1, None
    applied_so_far = 0
    for split in range(-1, len(order)):
        if split >= 0:
            applied_so_far += verdict[split] is True
        mistakes = unapplied_before[split + 1] + (applied_total - applied_so_far)
        if fewest is None or mistakes < fewest:
            best, fewest = split, mistakes

    truth = order[best] if best >= 0 else None
    head = order[-1]

    if truth is None:
        print(
            "The database holds nothing that the migrations create, so it has no "
            "schema yet.\nCreate one with `make db_init`, which builds it from the "
            "models, and then record\nthat with `alembic stamp head`."
        )
        return 1

    print(f"alembic_version says:  {', '.join(recorded) or 'nothing'}")
    print(f"The schema matches:    {truth}")
    if fewest:
        # Migrations that work through op.execute, and columns the models create
        # anyway, leave the evidence slightly ragged. A handful is normal.
        print(
            f"                       ({fewest} of {len(order)} revisions disagree; "
            "--verbose lists them)"
        )
    if truth == head:
        print("\nThe schema is up to date.")

    if recorded and truth in recorded:
        print("\nThe two agree, so there is nothing to repair.")
        return 0

    if set(recorded) & set(order[best + 1 :]):
        print(
            f"\nThe schema is {len(order) - 1 - best} revisions behind what "
            "has been recorded,\nso those migrations were skipped rather than "
            "applied. To replay them, set\nthe recorded revision back to the one "
            "the schema matches and upgrade:\n"
            f"\n    python tools/db_revision_from_schema.py --stamp\n"
            "    make db_migrate\n"
        )
        report_collisions(order, verdict, markers, present, best)
    else:
        print(
            "\nThe schema is ahead of what has been recorded, which happens when "
            "tables\nare created from the models rather than by migrations. "
            "Stamping records\nthe schema as it is, without changing it:\n"
            f"\n    python tools/db_revision_from_schema.py --stamp\n"
        )

    if not args.stamp:
        return 1

    if not args.yes:
        answer = input(f"\nSet alembic_version to {truth}? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Left alone.")
            return 1

    with engine.begin() as connection:
        # a database built from the models has no version table until it is
        # stamped for the first time
        connection.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            )
        )
        connection.execute(sa.text("DELETE FROM alembic_version"))
        connection.execute(
            sa.text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": truth},
        )
    rest = "" if truth == head else " Run `make db_migrate` to apply the rest."
    print(f"alembic_version set to {truth}.{rest}")
    return 0


sys.exit(main())
