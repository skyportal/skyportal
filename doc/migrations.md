# Database migrations

To bring a database up to date, run `make db_migrate`. It applies any pending
migrations, with `PYTHONPATH` and the config flag already set. This is one step
of [updating an existing checkout](setup).

The rest of this page is about writing migrations, which you need only if you
are changing the database schema yourself.

## Setting up

If you are planning to use database migrations, you need to let
Alembic know the current state of the database.

Presuming you've just started off by running `make load_demo_data`
on the latest main branch commit (this should happen on a vanilla main branch,
i.e. without any of your changes to the database schema),
tell Alembic that you are on the latest database schema:

```
PYTHONPATH=. alembic -x config=config.yaml stamp head
```

## Generate migration script

To generate a migration script, after having stamped the latest main commit (see above),
ensure that the app is stopped, check out the branch with the relevant DB schema
changes, and run the following:

```
PYTHONPATH=. alembic -x config=config.yaml revision --autogenerate -m "Revision description"
```

Review the resulting migration file under `alembic/versions` at hand of the [documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

Autogenerate compares the models to the current state of your database, so run
it only after applying any pending migrations. Otherwise the generated script
will also contain the changes those migrations make.

Delete the file if it does not describe your own schema changes. Any file in
`alembic/versions` counts as a revision, including one that only you have.

## Applying migration scripts

If the database has been stamped, as outlined above, the migration manager service
will automatically apply any pending migration scripts upon starting the app.

To manually apply migration scripts, after ensuring that the app is stopped, check
out the branch with pending migration scripts, and run the following to upgrade:

```
PYTHONPATH=. alembic -x config=config.yaml upgrade head
```

## Multiple heads

`alembic upgrade head` fails if more than one revision is a head, since it
cannot tell which one is meant:

```
Multiple head revisions are present for given argument 'head'
```

To see them:

```
PYTHONPATH=. alembic -x config=config.yaml heads
```

Usually one of them is a leftover revision of your own, from an earlier
autogenerate run. `git status` shows it as untracked under `alembic/versions`.
Check whether it has been applied:

```
PYTHONPATH=. alembic -x config=config.yaml current
```

If it does not appear there, delete the file. The remaining head is then the one
to upgrade to. Do not merge the two, as that would keep the unwanted revision in
the history.

If both heads are revisions that belong in the repository, a branch has added a
migration alongside one that landed on main. Either edit your migration's
`down_revision` to point at main's head (simplest while your migration is
unreleased and nobody has applied it), or merge the two:

```
PYTHONPATH=. alembic -x config=config.yaml merge -m "merge heads" <rev1> <rev2>
```

The `Test SkyPortal migrations` CI job runs the migrations from an empty
database, and will report a divergence before it reaches anyone else.
