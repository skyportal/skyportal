'''Test fixture configuration.'''

import pytest
import os
import uuid
import pathlib
from psycopg2 import OperationalError
from baselayer.app import models
from baselayer.app.config import load_config
from baselayer.app.test_util import (driver, MyCustomWebDriver,
                                     set_server_url, reset_state)
from skyportal.tests.fixtures import TMP_DIR, SourceFactory, GroupFactory, UserFactory
from skyportal.model_util import create_token


print('Loading test configuration from _test_config.yaml')
basedir = pathlib.Path(os.path.dirname(__file__))
cfg = load_config([(basedir/'../../test_config.yaml').absolute()])
set_server_url(f'http://localhost:{cfg["ports.app"]}')
print('Setting test database to:', cfg['database'])
models.init_db(**cfg['database'])


@pytest.fixture()
def public_group():
    return GroupFactory()


@pytest.fixture()
def public_source(public_group):
    return SourceFactory(groups=[public_group])


@pytest.fixture()
def private_source():
    return SourceFactory(groups=[])


@pytest.fixture()
def user(public_group):
    return UserFactory(groups=[public_group],
                       roles=[models.Role.query.get('Full user')])


@pytest.fixture()
def view_only_user(public_group):
    return UserFactory(groups=[public_group],
                       roles=[models.Role.query.get('View only')])


@pytest.fixture()
def group_admin_user(public_group):
    return UserFactory(groups=[public_group],
                       roles=[models.Role.query.get('Group admin')])


@pytest.fixture()
def super_admin_user(public_group):
    return UserFactory(groups=[public_group],
                       roles=[models.Role.query.get('Super admin')])


@pytest.fixture()
def view_only_token(user):
    token_id = create_token(permissions=[], created_by_id=user.id,
                            name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def manage_sources_token(group_admin_user):
    token_id = create_token(permissions=['Manage sources'],
                            created_by_id=group_admin_user.id,
                            name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def upload_data_token(user):
    token_id = create_token(permissions=['Upload data'],
                            created_by_id=user.id,
                            name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def manage_groups_token(super_admin_user):
    token_id = create_token(permissions=['Manage groups'],
                            created_by_id=super_admin_user.id,
                            name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def manage_users_token(super_admin_user):
    token_id = create_token(permissions=['Manage users'],
                            created_by_id=super_admin_user.id,
                            name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def comment_token(user):
    token_id = create_token(permissions=['Comment'],
                            created_by_id=user.id,
                            name=str(uuid.uuid4()))
    return token_id
