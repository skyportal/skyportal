'''Test fixture configuration.'''

import pytest
import os
import pathlib
from pytest_factoryboy import register, LazyFixture
from baselayer.app import models
from baselayer.app.config import load_config
from baselayer.app.test_util import (driver, MyCustomWebDriver, set_server_url,
                                     reset_state)
from skyportal.model_util import setup_permissions
from skyportal.tests.fixtures import TMP_DIR, SourceFactory, GroupFactory, UserFactory


print('Loading test configuration from _test_config.yaml')
basedir = pathlib.Path(os.path.dirname(__file__))
cfg = load_config([(basedir/'../../test_config.yaml').absolute()])
set_server_url(f'http://localhost:{cfg["ports:app"]}')
print('Setting test database to:', cfg['database'])
models.init_db(**cfg['database'])


@pytest.fixture(scope='session', autouse=True)
def add_acls(request):
    """Create roles/ACLs needed by application."""
    setup_permissions()
    """TODO Allow admin user to change to another user for testing.
    role = models.Role.query.get('Test user')
    if role is None:
        role = models.Role(id='Test user')
        role.acls = [models.ACL(id='System admin')]
    username = 'testuser@cesium-ml.org'
    u = models.User.query.filter(models.User.username ==
                                 'testuser@cesium-ml.org').first()
    if u is None:
        u = models.User(username=username)
    if role not in u.roles:
        u.roles.append(role)
    models.DBSession().add(u)
    models.DBSession().commit()
    """


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
@pytest.fixture(autouse=True)
def public_group():
    return GroupFactory()


@pytest.fixture(autouse=True)
def public_source(public_group):
    return SourceFactory(groups=[public_group])


@pytest.fixture(autouse=True)
def private_source():
    return SourceFactory(groups=[])


@pytest.fixture(autouse=True)
def user(public_group):
    return UserFactory(groups=[public_group],
                       roles=[models.Role.query.get('Full user')])
