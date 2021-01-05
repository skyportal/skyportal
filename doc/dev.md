# Developer notes

## Pre-commit hook

Install our pre-commit hook as follows:

```
pip install pre-commit
pre-commit install
```

This will check your changes before each commit to ensure that they
conform with our code style standards. We use black to reformat Python
code, and PrettierJS for JavaScript.  We also run ESLint to catch
several common Redux usage bugs.

## Testing

To execute the test suite:

- Install geckodriver and Firefox
- To run all tests: `make test`
- To run a single test: `./tools/test_frontend.py skportal/tests/frontend/<test_file>.py::test_<specific_test>`

This fires up the test server and runs that test. To make things
faster you can also run the test server separately:

```
make run_testing   # fire up the server with `test_conf.yaml`

pytest skyportal/tests/api  # test api
pytest skyportal/tests/frontend/test_user.py  # run subset of frontend tests
pytest skyportal/tests/frontend/test_user.py::test_user_profile_fetching  # run a single test
```

On Linux, the tests can be run in "headless" mode (no browser display):

- Install xfvb (`sudo apt-get install xfvb`)
- `make test_headless`

Or, as described above, launch the test server with `make run_testing`, and then call

```
xvfb-run pytest skyportal/tests/frontend/test_user.py
```

It is not noticeably faster to run the test suite headlessly.

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

## Docker images

Run `make docker-images` to build and push to Docker hub.

## Debugging GitHub Actions

You can insert the following step to debug your workflow:

```yaml
  - name: Setup tmate session
    uses: mxschmitt/action-tmate@v2
```

It will print a command that you can use to SSH into the runner.
