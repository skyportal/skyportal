'''Test fixture configuration.'''

import pytest
import os
import pathlib
from psycopg2 import OperationalError
from pytest_factoryboy import register, LazyFixture
from baselayer.app import models
from baselayer.app.config import load_config
from baselayer.app.test_util import (driver, MyCustomWebDriver,
                                     set_server_url, reset_state)
from skyportal.tests.fixtures import TMP_DIR, SourceFactory, GroupFactory, UserFactory


print('Loading test configuration from _test_config.yaml')
basedir = pathlib.Path(os.path.dirname(__file__))
cfg = load_config([(basedir/'../../test_config.yaml').absolute()])
set_server_url(f'http://localhost:{cfg["ports:app"]}')
print('Setting test database to:', cfg['database'])
models.init_db(**cfg['database'])


"""TODO
pytest-factoryboy seems like more trouble than it's worth here.
For now, I'm switching back to creating my own regular old pytest fixtures;
this could be problematic in the future if we end needing any tricky circular
dependenices, but it's much simpler than trying to keep track of how all the
variable injection performed by `pytest_factoryboy.register` is working.
"""
#register(GroupFactory, "group")
#register(GroupSourceFactory)
#register(SourceFactory, "private_source", id="private_source")
#register(SourceWithGroupFactory, "public_source", id="public_source",
#         group=LazyFixture("group"))


# TODO can we remove `autouse` here?
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
def super_admin_user(public_group):
    return UserFactory(groups=[public_group],
                       roles=[models.Role.query.get('Super admin')])
