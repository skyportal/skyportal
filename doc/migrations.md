# Database migrations

## Upgrade to latest

```
PYTHONPATH=. alembic upgrade head
```

## Generate migration

```
PYTHONPATH=. alembic revision --autogenerate -m "Initial revision"
```

Review the resulting migration file under `alembic/versions` at hand of the [documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).
