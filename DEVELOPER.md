# Developer Notes

## Connecting to the DB from IPython

The following snippet loads the config file and initializes a
connection to the database:

```
from skyportal import app_server
from skyportal.models import DBSession, init_db
cfg = app_server.load_config()
init_db(**cfg['database'])
```

Models can be queried directly, e.g.,

```
from skyportal.models import User
User.query.all()
```

The session object allows various DB state operations:

- `DBSession().add(obj)` -- add a new object into the DB
- `DBSession().commit()` -- commit modifications to objects
- `DBSession().rollback()` -- recover after a DB error
