# Developer notes

## Testing

To execute the test suite:

- Install geckodriver and Firefox
- To run all tests: `make test`
- To run a single test: `./tools/test_frontend.py skportal/tests/frontend/<test_file>.py::test_<specific_test>`

This fires up the test server and runs that test.  To make things
faster you can also run the test server separately:

```
make run_testing   # fire up the server with `test_conf.yaml`

pytest skyportal/tests/api  # test api
pytest skyportal/tests/frontend/test_user.py  # run subset of frontend tests
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

### Scheduling a `pg_cron` job to periodically delete old candidates not saved as sources

You may wish to configure SkyPortal to periodically delete old candidates not saved as sources. This section will outline that process using the Postgres extension [`pg_cron`](https://github.com/citusdata/pg_cron) in Ubuntu or other Debian-based distros.

The `pg_cron` installation and setup instructions here largely mirror those in the [official docs](https://github.com/citusdata/pg_cron#setting-up-pg_cron).

To install the `pg_cron` extension, run (assuming Postgres 11 -- replace the version number to match yours)
```
sudo apt -y install postgresql-11-cron
```
Then add the following two lines to bottom of postgresql.conf (typically located at /etc/postgresql/11/main/postgresql.conf):
```
shared_preload_libraries = 'pg_cron'
cron.database_name = 'skyportal'
```
Then, after restarting Postgres (`sudo service postgresql restart`), add the extension by running the following command in psql as superuser:
```
CREATE EXTENSION pg_cron;
```
If using the default SkyPortal DB configuration, this can be achieved by running
```
sudo psql -U skyportal -h localhost -p 5432 -c "CREATE EXTENSION pg_cron;"
```

Now add the cron job by running
```
SELECT cron.schedule('0 1 * * 6', $$DELETE FROM candidates WHERE source_id IS NULL AND created_at < now() - interval '1 month'$$);
```
This will run the command every Saturday at 1am UTC (change as desired), and will delete candidates not flagged as sources older than one month (configure as needed).

View all pg_cron jobs by running `SELECT * FROM cron.job;`, and you will see your new job:
```
skyportal=# SELECT * FROM cron.job;
 jobid | schedule  |                                          command                                           | nodename  | nodeport | database  | username  | active
-------+-----------+--------------------------------------------------------------------------------------------+-----------+----------+-----------+-----------+--------
     1 | 0 1 * * 6 | DELETE FROM candidates WHERE source_id IS NULL AND created_at < now() - interval '1 month' | localhost |     5432 | skyportal | skyportal | t
(1 row)

```

You can check that your pg_cron jobs are running as expected by viewing the main Postgres log (typically /var/log/postgresql/postgresql-11-main.log).

## Standards

We use ESLint to ensure that our JavaScript & JSX code is consistent and conforms with recommended standards.

- Install ESLint using `make lint-install`.  This will also install a git pre-commit hook so that any commit is linted before it is checked in.
- Run `make lint`  to perform a style check

## Docker images

Run `make docker-images` to build and push to Docker hub.
