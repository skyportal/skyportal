# Setup
## Installation
- A Python 3.6 or later installation is required
- Install the following dependencies:
  - Supervisor (v>=3.0b2)
  - NGINX (v>=1.7)
  - PostgreSQL (v>=9.6)
  - Node.JS/npm (v>=5.8.0)

  - On macOS:
    - Clone the repo and start the virtual env:

      ```
      git clone https://github.com/skyportal/skyportal.git
      cd skyportal/
      virtualenv skyportal_env
      source skyportal_env/bin/activate
      ```
    - If using [Homebrew](http://brew.sh/): `brew install supervisor nginx postgresql node`
      - If running the test suite, `geckodriver` is also needed: `brew install geckodriver`
    - Start the postgresql server:
      - to start automatically at login: `brew services start postgresql`
      - to start manually: `pg_ctl -D /usr/local/var/postgres start`
  - On Linux:
    - Using `apt`: `sudo apt install nginx supervisor postgresql libpq-dev npm nodejs-legacy`
    - It may be necessary to configure your database permissions: at the end of your `pg_hba.conf` (typically in `/etc/postgresql/9.6/main`), add the following lines and restart PostgreSQL (`sudo service postgresql restart`):
      ```
      local all postgres peer
      local skyportal skyportal trust
      local skyportal_test skyportal trust
      ```
    - If running the test suite, install `geckodriver`:
      ```
      GECKO_VER=0.24.0
      wget https://github.com/mozilla/geckodriver/releases/download/v${GECKO_VER}/geckodriver-v${GECKO_VER}-linux64.tar.gz
      sudo tar -xzf geckodriver-v${GECKO_VER}-linux64.tar.gz -C /usr/local/bin
      rm geckodriver-v${GECKO_VER}-linux64.tar.gz
      which geckodriver
      geckodriver --version
      ```

- Initialize the database with `make db_init` (also tests that your permissions have been properly configured)
- Run `make run` to start the server and navigate to `localhost:5000`

## Configuration
- Copy `config.yaml.defaults` to `config.yaml` and customize.
- Create admin user: `from skyportal.model_util import add_super_user; add_super_user('testuser@cesium-ml.org')`
- Optionally, add test data into the database: `python skyportal/model_util.py` (also initializes `testuser@cesium-ml.org` as an admin)
- If you want other users to be able to access the server:
  - #TODO Serve on 127.0.0.1 instead of 0.0.0.0 unless debug login is disabled?
  - Provide Google auth credentials, obtained as described in the config file.
- Under `app`, modify the `secret-key` as described in the config file.
