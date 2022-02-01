# Setup

## Dependencies

SkyPortal requires the following software to be installed.  We show
how to install them on MacOS and Debian-based systems below.

- Python 3.8 or later
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

If you are using Windows Subsystem for Linux (WSL) be sure you clone the repository onto a location on the virtual machine, not the mounted Windows drive. Additionally, we recommend that you use WSL 2, and not WSL 1, in order to avoid complications in interfacing with the Linux image's `localhost` network.

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

4. To build the docs, you'll need graphviz:
```
brew install graphviz
```

## Installation: Debian-based Linux and WSL

1. Install dependencies

```
sudo apt install nginx supervisor postgresql libpq-dev npm python3-pip
```

2. Configure your database permissions.

In `pg_hba.conf` (typically located in
`/etc/postgresql/<postgres-version>/main`), insert the following lines
*before* any other `host` lines:

```
host skyportal skyportal 127.0.0.1/32 trust
host skyportal_test skyportal 127.0.0.1/32 trust
```

In some PostgreSQL installations, the default TCP port may be different from the 5432 value assumed in our default configuration file values. To remedy this, you can either edit your config.yaml file to reflect your system's PostgreSQL default port, or update your system-wide config to use port 5432 by editing /etc/postgresql/12/main/postgresql.conf (replace "12" with your installed version number) and changing the line `port = XXXX` (where "XXXX" is whatever the system default was) to `port = 5432`.

Restart PostgreSQL:

```
sudo service postgresql restart
```

3. To run the test suite, you'll need Geckodriver:

- Download the latest version from https://github.com/mozilla/geckodriver/releases/
- Extract the binary to somewhere on your path
- Ensure it runs with `geckodriver --version`

In later versions of Ubuntu (16.04+), you can install Geckodriver through apt:
```
sudo apt install firefox-geckodriver
```

4. To build the docs, you'll need graphviz:
```
sudo apt install graphviz-dev graphviz
```

## Launch

1. Initialize the database with `make db_init` (this only needs to
   happen once).
2. Copy `config.yaml.defaults` to `config.yaml`.
3. Run `make log` to monitor the service and, in a separate window, `make run` to start the server.
4. Direct your browser to `http://localhost:5000`.
5. If you want some test data to play with, run `make load_demo_data` (do this while the server is running!).
6. Change users by navigating to `http://localhost:5000/become_user/<#>` where # is a number from 1-5.
   Different users have different privileges and can see more or less of the demo data.

## Troubleshooting

If you have trouble getting the demo data try doing

```make db_clear && make db_init && make run```

and then, from a different window, do `make load_demo_data`.

If you are using WSL, be sure everything (the git repository and all dependencies) are on the Linux machine and not the Windows side, as connection oddities can otherwise cause several errors.

## Additional Configuration

The configuration file lives in `config.yaml`, and is meant to be
self-documenting.  Please modify as you see fit.

**Before deploying this on a public server** change `app:secret-key`
to a unique value.

If you want to use a different configuration file, you may launch any
of the SkyPortal commands with the FLAGS environment variable set:

```
FLAGS="--config=myconfig.yaml" make run
```

### Authentication

By default, the server allows anyone to log in (even if it presents a
login screen).  If you are running a public-facing instance of
SkyPortal, you should enable multi-user login by adding Google
credentials to the `server:auth` section of the configuration file and
setting `debug_login` to `False`.

### Creating an administrative user

By default, no user has permission to perform system administration.
You can add a user with such permissions by running the following from
Python:

```
from skyportal.model_util import make_super_user
make_super_user('your@email.address.org')
```

### Test data

By default, SkyPortal contains no data.  You can ingest some sample light curves by running

```
make load_demo_data
```

This also adds `testuser@cesium-ml.org` as an administrator.
