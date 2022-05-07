# Database migrations

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

## Applying migration scripts

If the database has been stamped, as outlined above, the migration manager service
will automatically apply any pending migration scripts upon starting the app.

To manually apply migration scripts, after ensuring that the app is stopped, check
out the branch with pending migration scripts, and run the following to upgrade:

```
PYTHONPATH=. alembic -x config=config.yaml upgrade head
```
