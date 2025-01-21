from logging.config import fileConfig

from alembic import context

# These imports need to happen for their side-effects of registering models
from baselayer.app import models as baselayer_models  # noqa
from baselayer.app import psa  # noqa
from baselayer.app.config import load_config
from baselayer.app.models import init_db
from skyportal import models  # noqa

config_arg = context.get_x_argument(as_dictionary=True).get("config")
skyportal_configs = config_arg.split(":") if config_arg else []
cfg = load_config(config_files=skyportal_configs)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = baselayer_models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    db = cfg["database"]
    user = db["user"]
    password = db.get("password", "") or ""
    host = db["host"]

    url = f"postgresql://{user}:{password}@/{host}/{db['database']}"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = init_db(**cfg["database"])

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
