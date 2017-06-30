`alembic` configuration for SQLAlchemy migrations.

1) Alter the database schema in `models.py`.

2) Generate a migration using `alembic revision`:

```
PYTHONPATH=. alembic revision --autogenerate -m "<comment>"
```

3) Validate and commit the resulting file.

4) Perform the resulting upgrades with `alembic upgrade`:

```
PYTHONPATH=. alembic upgrade head
```

STILL TODO:
1) Deprecate `create_tables`, run migrations when starting the app

2) How to handle `skyportal_test` database?
