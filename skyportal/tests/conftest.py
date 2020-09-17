"""Test fixture configuration."""

import pytest
import os
import uuid
import pathlib
from datetime import datetime

from baselayer.app import models
from baselayer.app.config import load_config
from baselayer.app.test_util import (  # noqa: F401
    driver,
    set_server_url,
)

from skyportal.tests.fixtures import TMP_DIR  # noqa: F401
from skyportal.tests.fixtures import (
    ObjFactory,
    StreamFactory,
    GroupFactory,
    UserFactory,
    FilterFactory,
    InstrumentFactory,
    ObservingRunFactory,
    TelescopeFactory,
)
from skyportal.model_util import create_token
from skyportal.models import (
    DBSession,
    Source,
    Candidate,
    Role,
    User,
    Allocation,
    FollowupRequest,
)

import astroplan
import warnings
from astroplan import utils as ap_utils


print("Loading test configuration from _test_config.yaml")
basedir = pathlib.Path(os.path.dirname(__file__))
cfg = load_config([(basedir / "../../test_config.yaml").absolute()])
set_server_url(f'http://localhost:{cfg["ports.app"]}')
print("Setting test database to:", cfg["database"])
models.init_db(**cfg["database"])

# Add a "test factory" User so that all factory-generated comments have a
# proper author, if it doesn't already exist (the user may already be in
# there if running the test server and running tests individually)
if not DBSession.query(User).filter(User.username == "test factory").scalar():
    DBSession.add(User(username="test factory"))
    DBSession.commit()


def pytest_runtest_setup(item):
    # Print timestamp when running each test
    print(datetime.now().strftime('[%H:%M:%S] '), end='')


@pytest.fixture(scope='session')
def iers_data():
    # grab the latest earth orientation data for observatory calculations
    if ap_utils.IERS_A_in_cache():
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "error", category=astroplan.OldEarthOrientationDataWarning
            )
            try:
                ap_utils._get_IERS_A_table()
            except astroplan.OldEarthOrientationDataWarning:
                astroplan.download_IERS_A()


@pytest.fixture()
def public_stream():
    return StreamFactory()


@pytest.fixture()
def stream_with_users(super_admin_user, group_admin_user, user, view_only_user):
    return StreamFactory(
        users=[super_admin_user, group_admin_user, user, view_only_user]
    )


@pytest.fixture()
def public_group():
    return GroupFactory()


@pytest.fixture()
def public_group2():
    return GroupFactory()


@pytest.fixture()
def group_with_stream(
    super_admin_user, group_admin_user, user, view_only_user, public_stream
):
    return GroupFactory(
        users=[super_admin_user, group_admin_user, user, view_only_user],
        streams=[public_stream],
    )


@pytest.fixture()
def group_with_stream_with_users(
    super_admin_user, group_admin_user, user, view_only_user, stream_with_users
):
    return GroupFactory(
        users=[super_admin_user, group_admin_user, user, view_only_user],
        streams=[stream_with_users],
    )


@pytest.fixture()
def public_filter(public_group, public_stream):
    return FilterFactory(group=public_group, stream=public_stream)


@pytest.fixture()
def public_source(public_group):
    obj = ObjFactory(groups=[public_group])
    DBSession.add(Source(obj_id=obj.id, group_id=public_group.id))
    DBSession.commit()
    return obj


@pytest.fixture()
def public_source_two_groups(public_group, public_group2):
    obj = ObjFactory(groups=[public_group, public_group2])
    for group in [public_group, public_group2]:
        DBSession.add(Source(obj_id=obj.id, group_id=group.id))
    DBSession.commit()
    return obj


@pytest.fixture()
def public_source_group2(public_group2):
    obj = ObjFactory(groups=[public_group2])
    DBSession.add(Source(obj_id=obj.id, group_id=public_group2.id))
    DBSession.commit()
    return obj


@pytest.fixture()
def public_candidate(public_filter):
    obj = ObjFactory(groups=[public_filter.group])
    DBSession.add(Candidate(obj=obj, filter=public_filter))
    DBSession.commit()
    return obj


@pytest.fixture()
def red_transients_group(group_admin_user, view_only_user):
    return GroupFactory(
        name=f'red transients-{uuid.uuid4().hex}',
        users=[group_admin_user, view_only_user],
    )


@pytest.fixture()
def ztf_camera():
    return InstrumentFactory()


@pytest.fixture()
def keck1_telescope():
    observer = astroplan.Observer.at_site('Keck')
    return TelescopeFactory(
        name=f'Keck I Telescope_{uuid.uuid4()}',
        nickname='Keck1_{uuid.uuid4()}',
        lat=observer.location.lat.to('deg').value,
        lon=observer.location.lon.to('deg').value,
        elevation=observer.location.height.to('m').value,
        diameter=10.0,
    )


@pytest.fixture()
def p60_telescope():
    observer = astroplan.Observer.at_site('Palomar')
    return TelescopeFactory(
        name=f'Palomar 60-inch telescope_{uuid.uuid4()}',
        nickname='p60_{uuid.uuid4()}',
        lat=observer.location.lat.to('deg').value,
        lon=observer.location.lon.to('deg').value,
        elevation=observer.location.height.to('m').value,
        diameter=1.6,
    )


@pytest.fixture()
def lris(keck1_telescope):
    return InstrumentFactory(
        name=f'LRIS_{uuid.uuid4()}',
        type='imaging spectrograph',
        telescope=keck1_telescope,
        band='Optical',
        filters=[
            'sdssu',
            'sdssg',
            'sdssr',
            'sdssi',
            'sdssz',
            'bessellux',
            'bessellv',
            'bessellb',
            'bessellr',
            'besselli',
        ],
    )


@pytest.fixture()
def sedm(p60_telescope):
    return InstrumentFactory(
        name=f'SEDM_{uuid.uuid4()}',
        type='imaging spectrograph',
        telescope=p60_telescope,
        band='Optical',
        filters=['sdssu', 'sdssg', 'sdssr', 'sdssi'],
        api_classname='SEDMAPI',
        listener_classname='SEDMListener',
    )


@pytest.fixture()
def red_transients_run():
    return ObservingRunFactory()


@pytest.fixture()
def private_source():
    return ObjFactory(groups=[])


@pytest.fixture()
def user(public_group):
    return UserFactory(
        groups=[public_group], roles=[models.Role.query.get("Full user")]
    )


@pytest.fixture()
def user_no_groups():
    return UserFactory(roles=[models.Role.query.get("Full user")])


@pytest.fixture()
def user_two_groups(public_group, public_group2):
    return UserFactory(
        groups=[public_group, public_group2], roles=[models.Role.query.get("Full user")]
    )


@pytest.fixture()
def view_only_user(public_group):
    return UserFactory(
        groups=[public_group], roles=[models.Role.query.get("View only")]
    )


@pytest.fixture()
def group_admin_user(public_group):
    return UserFactory(
        groups=[public_group], roles=[models.Role.query.get("Group admin")]
    )


@pytest.fixture()
def group_admin_user_two_groups(public_group, public_group2):
    return UserFactory(
        groups=[public_group, public_group2],
        roles=[models.Role.query.get("Group admin")],
    )


@pytest.fixture()
def super_admin_user(public_group):
    return UserFactory(
        groups=[public_group], roles=[models.Role.query.get("Super admin")]
    )


@pytest.fixture()
def super_admin_user_two_groups(public_group, public_group2):
    return UserFactory(
        groups=[public_group, public_group2],
        roles=[models.Role.query.get("Super admin")],
    )


@pytest.fixture()
def view_only_token(user):
    token_id = create_token(ACLs=[], user_id=user.id, name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def view_only_token_two_groups(user_two_groups):
    token_id = create_token(ACLs=[], user_id=user_two_groups.id, name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def manage_sources_token(group_admin_user):
    token_id = create_token(
        ACLs=["Manage sources"], user_id=group_admin_user.id, name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def manage_sources_token_two_groups(group_admin_user_two_groups):
    token_id = create_token(
        ACLs=["Manage sources"],
        user_id=group_admin_user_two_groups.id,
        name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def upload_data_token(user):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )
    return token_id


@pytest.fixture()
def upload_data_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user_two_groups.id, name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def manage_groups_token(super_admin_user):
    token_id = create_token(
        ACLs=["Manage groups"], user_id=super_admin_user.id, name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def manage_users_token(super_admin_user):
    token_id = create_token(
        ACLs=["Manage users"], user_id=super_admin_user.id, name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def super_admin_token(super_admin_user):
    role = Role.query.get("Super admin")
    token_id = create_token(
        ACLs=[a.id for a in role.acls],
        user_id=super_admin_user.id,
        name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def super_admin_token_two_groups(super_admin_user_two_groups):
    role = Role.query.get("Super admin")
    token_id = create_token(
        ACLs=[a.id for a in role.acls],
        user_id=super_admin_user_two_groups.id,
        name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def comment_token(user):
    token_id = create_token(ACLs=["Comment"], user_id=user.id, name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def classification_token(user):
    token_id = create_token(ACLs=["Classify"], user_id=user.id, name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def taxonomy_token(user):
    token_id = create_token(
        ACLs=["Post taxonomy", "Delete taxonomy"],
        user_id=user.id,
        name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def taxonomy_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Post taxonomy", "Delete taxonomy"],
        user_id=user_two_groups.id,
        name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def comment_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Comment"], user_id=user_two_groups.id, name=str(uuid.uuid4())
    )
    return token_id


@pytest.fixture()
def public_group_sedm_allocation(sedm, public_group):
    allocation = Allocation(
        instrument=sedm,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )
    DBSession().add(allocation)
    DBSession().commit()
    return allocation


@pytest.fixture()
def public_group2_sedm_allocation(sedm, public_group2):
    allocation = Allocation(
        instrument=sedm,
        group=public_group2,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )
    DBSession().add(allocation)
    DBSession().commit()
    return allocation


@pytest.fixture()
def public_source_followup_request(public_group_sedm_allocation, public_source, user):
    fr = FollowupRequest(
        obj=public_source,
        allocation=public_group_sedm_allocation,
        payload={
            'priority': "5",
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
        },
        requester_id=user.id,
        last_modified_by_id=user.id,
    )

    DBSession().add(fr)
    DBSession().commit()
    return fr


@pytest.fixture()
def public_source_group2_followup_request(
    public_group2_sedm_allocation, public_source_group2, user_two_groups
):
    fr = FollowupRequest(
        obj=public_source_group2,
        allocation=public_group2_sedm_allocation,
        payload={
            'priority': "5",
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
        },
        requester_id=user_two_groups.id,
        last_modified_by_id=user_two_groups.id,
    )

    DBSession().add(fr)
    DBSession().commit()
    return fr


@pytest.fixture()
def sedm_listener_token(sedm, group_admin_user):
    token_id = create_token(
        ACLs=[sedm.listener_class.get_acl_id()],
        user_id=group_admin_user.id,
        name=str(uuid.uuid4()),
    )
    return token_id
