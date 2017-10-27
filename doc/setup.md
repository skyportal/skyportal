# Setup
## Installation
- A Python 3.6 or later installation is required
- Install the following dependencies: Supervisor, NGINX, PostgreSQL, Node.JS
  - On macOS:
    - Using [Homebrew](http://brew.sh/): `brew install supervisor nginx postgresql node`
    - Start the postgresql server:
      - to start automatically at login: `brew services start postgresql`
      - to start manually: `pg_ctl -D /usr/local/var/postgres start`
  - On Linux:
    - Using `apt-get`: `sudo apt-get install nginx supervisor postgresql libpq-dev npm nodejs-legacy`
    - It may be necessary to configure your database permissions: at the end of your `pg_hba.conf` (typically in `/etc/postgresql/9.6/main`), add the following lines and restart PostgreSQL (`sudo service postgresql restart`):
      ```
      local all postgres peer
      local skyportal skyportal trust
      local skyportal_test skyportal trust
      ```
- Initialize the database with `make db_init` (also tests that your permissions have been properly configured)
- Run `make` to start the server and navigate to `localhost:5000`

## Configuration
- Copy `config.yaml.defaults` to `config.yaml` and customize.
- Create admin user: `from skyportal.model_util import add_super_user; add_super_user('testuser@cesium-ml.org')`
- Optionally, add test data into the database: `python skyportal/model_util.py` (also initializes `testuser@cesium-ml.org` as an admin)
- If you want other users to be able to access the server:
  - #TODO Serve on 127.0.0.1 instead of 0.0.0.0 unless debug login is disabled?
  - Provide Google auth credentials, obtained as described in the config file.
- Under `app`, modify the `secret-key` as described in the config file.
