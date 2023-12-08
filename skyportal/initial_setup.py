import argparse
import os
from email.utils import parseaddr
from pathlib import Path

import model_util

from baselayer.app.env import load_env
from baselayer.app.model_util import create_tables, drop_tables, status
from baselayer.app.psa import TornadoStorage
from skyportal.models import Base, ThreadSession, User, init_db

"""
usage: initial_setup.py [-h] [--nodrop] [--adminusername ADMINUSER]
                        [--username USER]

Initialize Skyportal and add admin/users

optional arguments:
  -h, --help            show this help message and exit
  --nodrop              do not force drop existing databases
  --adminusername ADMINUSER
                        Email of the admin user (e.g., testuser@cesium-ml.org)
  --username USER       Email of a normal user (e.g., user@cesium-ml.org)

e.g.
PYTHONPATH=$PYTHONPATH:"." python skyportal/initial_setup.py  \
           --adminuser=<email> --user=<anotheremail>

If you just want to add a user to an existing database make sure you add the `--nodrop` flag:

PYTHONPATH=$PYTHONPATH:"." python skyportal/initial_setup.py  \
          --nodrop --user=<anotheremail>
"""

parser = argparse.ArgumentParser(description='Initialize Skyportal and add admin/users')
parser.add_argument(
    '--nodrop',
    action='store_true',
    default=False,
    dest='nodrop',
    help='do not force drop existing databases',
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

    if not results.nodrop:
        with status("Force dropping all tables"):
            drop_tables()

    with status(
        "Creating tables. If you really want to start from scratch,"
        " do a make db_clear; make db_init"
    ):
        create_tables()

    for model in Base.metadata.tables:
        print('    -', model)

    with status("Creating permissions"):
        model_util.setup_permissions()

    with ThreadSession() as session:
        if adminuser != '':
            with status(f"Creating super admin ({adminuser})"):
                super_admin_user = User(
                    username=results.adminuser, role_ids=['Super admin']
                )

                session.add_all([super_admin_user])

                for u in [super_admin_user]:
                    session.add(
                        TornadoStorage.user.create_social_auth(
                            u, u.username, 'google-oauth2'
                        )
                    )
        if user != '':
            with status(f"Creating user ({user})"):
                user = User(username=results.user, role_ids=['Full user'])

                session.add_all([user])

                for u in [user]:
                    session.add(
                        TornadoStorage.user.create_social_auth(
                            u, u.username, 'google-oauth2'
                        )
                    )
        if adminuser == '' and results.adminuser is not None:
            print("Note: adminuser is not a valid email address")
        if user == '' and results.user is not None:
            print("Note: user is not a valid email address")
