# Developer notes
## Testing
To execute the test suite:

- Install ChromeDriver from [https://sites.google.com/a/chromium.org/chromedriver/home](https://sites.google.com/a/chromium.org/chromedriver/home)
- Install Chrome or Chromium
- To run all tests: `make test`
- To run a single test: `./tools/test_frontend.py skportal/tests/frontend/<test_file>.py::test_<specific_test>`

On Linux, the tests can be run in "headless" mode (no browser display):
  - Install xfvb (`sudo apt-get install xfvb`)
  - `make test_headless`

## Debugging
- Run `make log` to watch log output
- Run `make stop` to stop any running web services.
- Run `make attach` to attach to output of webserver, e.g. for use with `pdb.set_trace()`
- Run `make check-js-updates` to see which Javascript packages are eligible for an upgrade.

## Database
All interactions with the database are performed by way of SQLAlchemy using the
Pyscopg2 backend. Some standard but not necessarily obvious usage patterns we
make use of include:

- Logic for connecting to the DB, refreshing tables, etc. is found in `baselayer/model_utils.py`:

```
from baselayer.app.env import load_env
from skyportal.models import DBSession, init_db
env, cfg = load_env()
init_db(**cfg['database'])
```

- The session object controls various DB state operations:

```
DBSession().add(obj)  # add a new object into the DB
DBSession().commit()  # commit modifications to objects
DBSession().rollback()  # recover after a DB error
```

- Generic logic applicable to any model is included in the base model class `baselayer.app.models.Base` (`to_dict`, `__str__`, etc.), but can be overridden within a specific model
- Models can be queried directly (`User.query.all()`), or more specific queries can be constructed via the session object (`DBSession().query(User.id).all()`)
- Convenience functionality:
    - Join relationships: some multi-step relationships are defined through joins using the `secondary` parameter to eliminate queries from the intermediate table; e.g., `User.acls` instad of `[r.acls for r in User.roles]`
    - [Association proxies](http://docs.sqlalchemy.org/en/latest/orm/extensions/associationproxy.html): shortcut to some attribute of a related object; e.g., `User.permissions` instead of `[a.id for a in User.acls]`
    - [Joined loads](http://docs.sqlalchemy.org/en/latest/orm/loading_relationships.html): this allows for a single query to also include child/related objects; often used in handlers when we know that information about related objects will also be needed.
    - `to_json()`: often from a handler we return an ORM object, which gets converted to JSON via `json_util.to_json(obj.to_dict())`. This also includes the attributes of any children that were loaded via `joinedload` or by accessing them directly. For example:
        - `User.query.first().to_dict()` will not contain information about the user's permissions
        - `u = User.query.first(); u.acls; u.to_dict()` does include a list of the user's ACLs

## Standards
We use ESLint to ensure that our JavaScript & JSX code is consistent and conforms with recommended standards.

- Install ESLint using `make lint-install`.  This will also install a git pre-commit hook so that any commit is linted before it is checked in.
- Run `make lint`  to perform a style check

## Docker images
Run `make docker-images` to build and push to Docker hub.
