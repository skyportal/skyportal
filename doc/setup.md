# Setup

## Dependencies

SkyPortal requires the following software to be installed.  We show
how to install them on MacOS and Debian-based systems below.

- Python 3.6 or later
- Supervisor (v>=3.0b2)
- NGINX (v>=1.7)
- PostgreSQL (v>=9.6)
- Node.JS/npm (v>=5.8.0)

## Source download, Python environment

Clone the [SkyPortal repository](https://github.com/skyportal/skyportal) and start a new
virtual environment.

```
git clone https://github.com/skyportal/skyportal.git
cd skyportal/
virtualenv skyportal_env
source skyportal_env/bin/activate
```

(You can also use `conda` or `pipenv` to create your environment.)

## Installation: MacOS

These instructions assume that you have [Homebrew](http://brew.sh/) installed.

1. Install dependencies

```
brew install supervisor nginx postgresql node
```

2. Start the PostgreSQL server:

  - To start automatically at login: `brew services start postgresql`
  - To start manually: `pg_ctl -D /usr/local/var/postgres start`

3. To run the test suite, you'll need Geckodriver:

```
brew install geckodriver
```

## Installation: Debian-based Linux

1. Install dependencies

```
sudo apt install nginx supervisor postgresql libpq-dev nodejs
```

2. Configure your database permissions.

At the end of `pg_hba.conf` (typically located in `/etc/postgresql/<postgres-version>/main`), add the following lines:

```
local all postgres peer
local skyportal skyportal trust
local skyportal_test skyportal trust
```

Restart PostgreSQL:

```
sudo service postgresql restart
```

3. To run the test suite, you'll need Geckodriver:

- Download the latest version from https://github.com/mozilla/geckodriver/releases/
- Extract the binary to somewhere on your path
- Ensure it runs with `geckodriver --version`

## Launch

1. Initialize the database with `make db_init` (this only needs to happen once).
2. If you want some test data to play with, run `make load_demo_data`.
3. Run `make log` to monitor the service and, in a separate window, `make run` to start the server.

Direct your browser to http://localhost:5000.

## Additional Configuration

The configuration file lives in `config.yaml`; start by copying
`config.yaml.defaults` to `config.yaml`.  The configuration file is
meant to be self-documenting.

Load the file into an editor, and change `app:secret-key` to a unique
value.

### Authentication

By default, the server allows anyone to log in (even if it presents a
login screen).  If you are running a public-facing instance of
SkyPortal, you should enable multi-user login by adding Google
credentials to the `server:auth` section of the configuration file.

### Creating an administrative user

By default, no user has permission to perform system administration.
You can add a user with such permissions by running the following from
Python:

```
from skyportal.model_util import add_super_user
add_super_user('testuser@cesium-ml.org')
```

### Test data

By default, SkyPortal contains no data.  You can ingest some sample light curves by running

```
make load_demo_data
```

This also adds `testuser@cesium-ml.org` as an administrator.
