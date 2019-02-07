# SkyPortal

SkyPortal is a web application that interactively displays scientific
datasets to astronomers for annotation, analysis, and discussion.  It
is designed to be modular and extensible, so it can be customized for
various scientific use-cases.

The base version of SkyPortal was designed with the Zwicky Transient
Facility, and eventually LSST, in mind.

Please [read the documentation](http://skyportal.io/docs/) for more on
installation, configuration, and development.

SkyPortal builds on top
of [baselayer](https://github.com/cesium-ml/baselayer), a scientific web
application platform developed by the same team.

## Installation on a Mac

- Clone the repo and start the virtual env:

```
git clone https://github.com/skyportal/skyportal.git
cd skyportal/
virtualenv skyportal_env
source skyportal_env/bin/activate
```

- Install dependencies and start postgres

```
brew install install supervisor nginx postgresql node geckodriver
brew services start postgresql
```

- Create the database

```
make db_init
```

- Start

```
cp docker.yaml config.yaml
```

edit `config.yaml` so that the database points to `localhost` then

```
PYTHONPATH=$PYTHONPATH:"." python skyportal/initial_setup.py  \
           --adminuser=<email>
make run
```
This will create an admin user with the username=`<email>`. If you want to add a normal user later on include
the `--nodrop` flag:

```
PYTHONPATH=$PYTHONPATH:"." python skyportal/initial_setup.py  \
          --nodrop --user=<anotheremail>
```

## To Use Locally with Docker-Compose

Make the docker image:

```
make docker-local
```

Start the docker compose

```
docker-compose up
```

Connect to the front-end at <a href="http://localhost:9000">http://localhost:9000</a>

## Developer notes

### Important Makefile targets

General:

- help : Describe make targets

DB preparation:

- db_init : Create database
- db_clear : Drop and re-create DB

Launching:

- debug : Launch app in debug mode, which auto-refreshes files and
          monitors micro-services
- log : Tail all log files

Testing:

- test : Launch web app & execute frontend tests
- test_headless : (Linux only) The above, but without a visible
                  browser

Development:

- lint : Run ESLint on all files.  Installs ESLint if necessary.
- lint-unix : Same as above, but outputs in a format that most text
              editors can parse
- lint-githook : Install a Git pre-commit hook that lints staged
                 chunks (this is done automatically when you lint
                 for the first time).
