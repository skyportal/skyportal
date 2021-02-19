import os
from pathlib import Path
import argparse
from email.utils import parseaddr
from baselayer.app.env import load_env
from baselayer.app import model_util as baselayer_model_util
from social_tornado.models import TornadoStorage
from skyportal import models

import model_util

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
          --nodrop --username=<anotheremail>
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

    with baselayer_model_util.status(
        f"Connecting to database {cfg['database']['database']}"
    ):
        models.init_db(**cfg['database'])

    if not results.nodrop:
        with baselayer_model_util.status("Force dropping all tables"):
            baselayer_model_util.drop_tables()

    with baselayer_model_util.status(
        "Creating tables. If you really want to start from scratch,"
        " do a make db_clear; make db_init"
    ):
        baselayer_model_util.create_tables()

    for model in models.Base.metadata.tables:
        print('    -', model)

    with baselayer_model_util.status("Creating permissions"):
        model_util.setup_permissions()

    if adminuser != '':
        with baselayer_model_util.status(f"Creating super admin ({adminuser})"):
            super_admin_user = models.User(
                username=results.adminuser, role_ids=['Super admin']
            )

            models.DBSession().add_all([super_admin_user])

            for u in [super_admin_user]:
                models.DBSession().add(
                    TornadoStorage.user.create_social_auth(
                        u, u.username, 'google-oauth2'
                    )
                )
    if user != '':
        with baselayer_model_util.status(f"Creating user ({user})"):
            user = models.User(username=results.user, role_ids=['Full user'])

            models.DBSession().add_all([user])

            for u in [user]:
                models.DBSession().add(
                    TornadoStorage.user.create_social_auth(
                        u, u.username, 'google-oauth2'
                    )
                )
    if adminuser == '' and results.adminuser is not None:
        print("Note: adminuser is not a valid email address")
    if user == '' and results.user is not None:
        print("Note: user is not a valid email address")
