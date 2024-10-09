# Developer notes

## Pre-commit hook

Install our pre-commit hook as follows:

```
pip install pre-commit
pre-commit install
```

This will check your changes before each commit to ensure that they
conform with our code style standards. We use black to reformat Python
code, and PrettierJS for JavaScript. We also run ESLint to catch
several common Redux usage bugs.

## Testing

To execute the test suite:

- Install geckodriver and Firefox
- To run all tests: `make test`
- To run a single test: `./baselayer/tools/test_frontend.py skyportal/tests/frontend/<test_file>.py::test_<specific_test>`

This fires up the test server and runs that test. To make things
faster you can also run the test server separately:

```
make run_testing   # fire up the server with `test_conf.yaml`

pytest skyportal/tests/api  # test api
pytest skyportal/tests/frontend/test_user.py  # run subset of frontend tests
pytest skyportal/tests/frontend/test_user.py::test_user_profile_fetching  # run a single test
```

On Linux, the tests can be run in "headless" mode (no browser display):

- Install xvfb (`sudo apt-get install xvfb`)
- `make test_headless`

Or, as described above, launch the test server with `make run_testing`, and then call

```
xvfb-run pytest skyportal/tests/frontend/test_user.py
```

It is not noticeably faster to run the test suite headlessly.

### Test fixtures

The SkyPortal test suite leverages pytest fixtures to generate and isolate test data for each test. Fixtures are declared in the `skyportal/tests/conftest.py` file, and they utilize factories implemented in `skyportal/tests/fixtures.py` to generate new instances of fixtures as needed.

Each test will request any fixtures that it requires, and as part of the set-up for that test, new test instances of the fixtures are created. This means that each test is guaranteed to work with fresh, isolated test data in order to avoid any unintended dependencies on other tests. Fixtures should be used when possible in writing new tests to promote safe, repeatable test results.

SkyPortal test fixtures are implemented with teardown logic, such that any database records generated for that fixture are deleted from the test database upon completion of a test. This serves to avoid bloating of the test database as more tests are run. Note that each fixture defined in `conftest.py` uses the `yield` keyword to return its test object. Any code following `yield` in a pytest fixture is run as teardown logic when that fixture goes out of scope; you will find that in SkyPortal this involves calling the relevant `teardown()` functions on the fixture objects created. These `teardown()` functions are implemented for each SQLAlchemyModelFactory subclass defined in `fixtures.py`.

Any new fixtures and fixture factories being added should follow this same structure, taking care to delete all fixture data (including SubFactory-generated records, i.e. a new User created to be the author of a new Comment). Foreign key constraints and cascade behavior defined on the database models can be used to simplify this logic but can also lead to subtle errors in tearing down fixtures and should be taken into careful consideration.

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
For more information on how to use the session, see `baselayer/doc/dev.md`.


- Generic logic applicable to any model is included in the base model class `baselayer.app.models.Base` (`to_dict`, `__str__`, etc.), but can be overridden within a specific model
- Models can be queried directly (`User.query.all()`), or more specific queries can be constructed via the session object (`DBSession().query(User.id).all()`)
- A more modern way to interact with the models is using select statements: `Obj.select(current_user_id).where(Obj.id == 'ZTF20aahxjps')`
- To get the actual objects create a session (either using `self.Session()` on the handler or using `DBSession()` which does not apply permissioning).
  Then use the session: `session.execute(stmt).all()` or `session.scalars(stmt).all()`. The `scalars` is preferred when selecting whole objects or single columns.
  The `execute` is better for getting multiple columns as tuples.
- Best practice is to call the session as a context manager (i.e., `with self.Session() as session:`) but only if the session does not need to stay open.
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

## Making a release

**Please also see [versioning](versioning).**

1. Update the version number in `skyportal/__init__.py`.
2. Commit the changes:
    ```
    git add skyportal/__init__.py
    git commit -am "Update version to v${NEW_VERSION}"
    ```
3. Tag & sign the release:
    ```
    git tag -s v${NEW_VERSION} -m "SkyPortal v${NEW_VERSION} release"
    ```
    (If you do not have a GPG key, follow the tutorial to set it up:
    https://help.github.com/articles/signing-commits-with-gpg/)
4. Push the changes:
    ```
    git push --tags origin main
    ```
    where `origin` points to the ``github.com:skyportal/skyportal`` repository.
5. Create a new release on GitHub, using the tag you just created. The release should be formatted as follows:
    - A title, in the form `SkyPortal v${NEW_VERSION} release (YYYY-MM-DD)`
    - A brief summary of the changes, including any breaking changes
    - A list of the changes split in the relevant categories (e.g., new features, bug fixes, frontend, backend, etc.). For each change, include a list of the associated PR numbers, as well as the GitHub usernames of the contributors.
    - If applicable, a migration guide to help users and/or admins upgrade to the new version.
