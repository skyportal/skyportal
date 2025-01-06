import argparse
import os
from email.utils import parseaddr
from pathlib import Path

import model_util

from baselayer.app.env import load_env
from baselayer.app.model_util import create_tables
from baselayer.tools.status import status
from baselayer.app.psa import TornadoStorage
from skyportal.models import Base, DBSession, User, init_db

"""
usage: initial_setup.py [-h] [--adminusername ADMINUSER]
                        [--username USER] [--config CONFIG]

Initialize Skyportal and add admin/users

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       Path to config file (default: config.yaml)
  --adminusername ADMINUSER
                        Email of the admin user (e.g., testuser@cesium-ml.org)
  --username USER       Email of a normal user (e.g., user@cesium-ml.org)

e.g.
PYTHONPATH=$PYTHONPATH:"." python skyportal/initial_setup.py  \
           --adminuser=<email> --user=<anotheremail>
"""

parser = argparse.ArgumentParser(
    description='Initialize Skyportal and optionally add admin/users'
)

parser.add_argument(
    '--config',
    dest='config',
    default='config.yaml',
    help='Path to config file (default: config.yaml)',
)

parser.add_argument(
    '--adminusername',
    dest='adminuser',
    default=None,
    help='Email of the admin user (e.g., testuser@cesium-ml.org)',
)

parser.add_argument(
    '--username',
    dest='user',
    default=None,
    help='Email of a normal user (e.g., user@cesium-ml.org)',
)

results = parser.parse_args()


if __name__ == "__main__":
    """Create the initial structure of the DB, prepping for Skyportal"""

    env, cfg = load_env()
    basedir = Path(os.path.dirname(__file__)) / '..'

    _, adminuser = parseaddr(results.adminuser)
    if adminuser == '' and results.adminuser is not None:
        print("Note: adminuser is not a valid email address")
    _, user = parseaddr(results.user)
    if user == '' and results.user is not None:
        print("Note: user is not a valid email address")

    with status(f"Connecting to database {cfg['database.database']}"):
        init_db(**cfg['database'])

    with status(
        f"Creating tables in database {cfg['database.database']} if they do not exist"
    ):
        create_tables()

    for model in Base.metadata.tables:
        print('    -', model)

    with status("Creating permissions"):
        model_util.setup_permissions()

    if adminuser != '':
        with status(f"Creating super admin ({adminuser})"):
            super_admin_user = User(
                username=results.adminuser, role_ids=['Super admin']
            )

            DBSession().add_all([super_admin_user])

            for u in [super_admin_user]:
                DBSession().add(
                    TornadoStorage.user.create_social_auth(
                        u, u.username, 'google-oauth2'
                    )
                )
    if user != '':
        with status(f"Creating user ({user})"):
            user = User(username=results.user, role_ids=['Full user'])

            DBSession().add_all([user])

            for u in [user]:
                DBSession().add(
                    TornadoStorage.user.create_social_auth(
                        u, u.username, 'google-oauth2'
                    )
                )
    if adminuser == '' and results.adminuser is not None:
        print("Note: adminuser is not a valid email address")
    if user == '' and results.user is not None:
        print("Note: user is not a valid email address")
