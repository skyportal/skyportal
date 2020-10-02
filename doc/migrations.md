# Database migrations

## Setting up

If you are planning to use database migrations, you need to let
Alembic know the current state of the database.

Presuming you've just started off by running `make load_demo_data`,
tell Alembic that you are on the latest database schema:

```
PYTHONPATH=. alembic stamp head
```

## Upgrade to latest

Subsequently, when the database schema changes, run the following to
upgrade:

```
PYTHONPATH=. alembic upgrade head
```

## Generate migration

```
PYTHONPATH=. alembic -x config=config.yaml revision --autogenerate -m "Revision description"
```

Review the resulting migration file under `alembic/versions` at hand of the [documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).
