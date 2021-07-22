"""Test fixture configuration."""

import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import astroplan
import numpy as np
import pytest

from baselayer.app import models
from baselayer.app.test_util import driver  # noqa: F401
from skyportal.model_util import create_token, delete_token
from skyportal.models import (
    DBSession,
    Source,
    Candidate,
    Role,
    User,
    GroupStream,
    StreamUser,
    GroupUser,
    GroupTaxonomy,
    GroupComment,
    GroupAnnotation,
    GroupClassification,
    GroupPhotometry,
    GroupSpectrum,
    FollowupRequestTargetGroup,
    Thumbnail,
)
from skyportal.tests.fixtures import (
    ObjFactory,
    StreamFactory,
    GroupFactory,
    UserFactory,
    FilterFactory,
    InstrumentFactory,
    ObservingRunFactory,
    TelescopeFactory,
    ClassicalAssignmentFactory,
    TaxonomyFactory,
    CommentFactory,
    AnnotationFactory,
    ClassificationFactory,
    FollowupRequestFactory,
    AllocationFactory,
    InvitationFactory,
    NotificationFactory,
    UserNotificationFactory,
    ThumbnailFactory,
)
from skyportal.tests.fixtures import TMP_DIR  # noqa: F401
from skyportal.models import Obj

# Add a "test factory" User so that all factory-generated comments have a
# proper author, if it doesn't already exist (the user may already be in
# there if running the test server and running tests individually)
if not DBSession.query(User).filter(User.username == "test factory").scalar():
    DBSession.add(User(username="test factory"))
    DBSession.commit()

# Also add the test driver user (testuser-cesium-ml-org) if needed so that the driver
# fixture has a user to login as (without needing an invitation token).
# With invitations enabled on the test configs, the driver fails to login properly
# without this user because the authenticator looks for the user or an
# invitation token when neither exists initially on fresh test databases.
if not DBSession.query(User).filter(User.username == "testuser-cesium-ml-org").scalar():
    DBSession.add(
        User(username="testuser-cesium-ml-org", oauth_uid="testuser@cesium-ml.org")
    )
    DBSession.commit()


def pytest_runtest_setup(item):
    # Print timestamp when running each test
    print(datetime.now().strftime('[%H:%M:%S] '), end='')


# set up a hook to be able to check if a test has failed
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object

    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"

    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture(scope="function", autouse=True)
def test_driver_user(request):
    """
    If a frontend test becomes some fixture-generated user, and the fixture
    user is subsequently deleted, than the driver will have no current_user.
    So, default back to the testuser-cesium-ml-org user upon frontend test
    completion.
    """
    yield  # Yield immediately since we only need to run teardown code
    if 'driver' in request.node.funcargs:
        testuser = (
            DBSession()
            .query(User)
            .filter(User.username == "testuser-cesium-ml-org")
            .first()
        )
        webdriver = request.node.funcargs['driver']
        webdriver.get(f"/become_user/{testuser.id}")


# check if a test has failed
@pytest.fixture(scope="function", autouse=True)
def test_failed_check(request):

    gecko = Path('geckodriver.log')
    gecko.touch(exist_ok=True)

    # get the number of bytes in the file currently
    log_bytes = os.path.getsize(gecko)

    # add a separator to the geckodriver logs
    with open(gecko, 'a') as f:
        f.write(f'BEGIN {request.node.nodeid}\n')

    yield
    # request.node is an "item" because we use the default
    # "function" scope

    # add a separator to the geckodriver logs
    with open(gecko, 'a') as f:
        f.write(f'END {request.node.nodeid}\n')

    if request.node.rep_call.failed and 'driver' in request.node.funcargs:
        webdriver = request.node.funcargs['driver']
        take_screenshot_and_page_source(webdriver, request.node.nodeid)

    # delete the interstitial data from the geckodriver log by
    # truncating the file back to its original number of bytes
    with open(gecko, 'a') as f:
        f.truncate(log_bytes)


# make a screenshot with a name of the test, date and time.
# also save the page HTML.
def take_screenshot_and_page_source(webdriver, nodeid):
    file_name = f'{nodeid}_{datetime.today().strftime("%Y-%m-%d_%H:%M")}.png'.replace(
        "/", "_"
    ).replace(":", "_")
    file_name = os.path.join(os.path.dirname(__file__), '../../test-results', file_name)
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)

    webdriver.save_screenshot(file_name)
    with open(file_name.replace('png', 'html'), 'w') as f:
        f.write(webdriver.page_source)

    file_name = (
        f'{nodeid}_{datetime.today().strftime("%Y-%m-%d_%H:%M")}.console.log'.replace(
            "/", "_"
        ).replace(":", "_")
    )
    file_name = os.path.join(
        os.path.dirname(__file__), '../../webdriver-console', file_name
    )
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)

    with open(file_name, 'w') as f, open('geckodriver.log', 'r') as gl:
        lines = gl.readlines()
        revlines = list(reversed(lines))
        istart = revlines.index(f'BEGIN {nodeid}\n')
        iend = revlines.index(f'END {nodeid}\n')
        f.write('\n'.join(list(reversed(revlines[iend : (istart + 1)]))))  # noqa: E203


@pytest.fixture()
def public_stream():
    stream = StreamFactory()
    # Save ID of new DB row
    stream_id = stream.id
    yield stream
    StreamFactory.teardown(stream_id)


@pytest.fixture()
def public_stream2():
    stream = StreamFactory()
    stream_id = stream.id
    yield stream
    StreamFactory.teardown(stream_id)


@pytest.fixture()
def stream_with_users(super_admin_user, group_admin_user, user, view_only_user):
    stream = StreamFactory(
        users=[super_admin_user, group_admin_user, user, view_only_user]
    )
    stream_id = stream.id
    yield stream
    StreamFactory.teardown(stream_id)


@pytest.fixture()
def public_group(public_stream):
    group = GroupFactory(streams=[public_stream])
    group_id = group.id
    yield group
    GroupFactory.teardown(group_id)


@pytest.fixture()
def public_group2(public_stream):
    group = GroupFactory(streams=[public_stream])
    group_id = group.id
    yield group
    GroupFactory.teardown(group_id)


@pytest.fixture()
def public_group_stream2(public_stream2):
    group = GroupFactory(streams=[public_stream2])
    group_id = group.id
    yield group
    GroupFactory.teardown(group_id)


@pytest.fixture()
def public_group_two_streams(public_stream, public_stream2):
    group = GroupFactory(streams=[public_stream, public_stream2])
    group_id = group.id
    yield group
    GroupFactory.teardown(group_id)


@pytest.fixture()
def public_group_no_streams():
    group = GroupFactory()
    group_id = group.id
    yield group
    GroupFactory.teardown(group_id)


@pytest.fixture()
def group_with_stream(
    super_admin_user, group_admin_user, user, view_only_user, public_stream
):
    group = GroupFactory(
        users=[super_admin_user, group_admin_user, user, view_only_user],
        streams=[public_stream],
    )
    group_id = group.id
    yield group
    GroupFactory.teardown(group_id)


@pytest.fixture()
def group_with_stream_with_users(
    super_admin_user, group_admin_user, user, view_only_user, stream_with_users
):
    group = GroupFactory(
        users=[super_admin_user, group_admin_user, user, view_only_user],
        streams=[stream_with_users],
    )
    group_id = group.id
    yield group
    GroupFactory.teardown(group_id)


@pytest.fixture()
def public_groupstream(public_group):
    return (
        DBSession()
        .query(GroupStream)
        .filter(
            GroupStream.group_id == public_group.id,
            GroupStream.stream_id == public_group.streams[0].id,
        )
        .first()
    )


@pytest.fixture()
def public_streamuser(public_stream, user):
    return (
        DBSession()
        .query(StreamUser)
        .filter(StreamUser.user_id == user.id, StreamUser.stream_id == public_stream.id)
        .first()
    )


@pytest.fixture()
def public_streamuser_no_groups(public_stream, user_no_groups):
    return (
        DBSession()
        .query(StreamUser)
        .filter(
            StreamUser.user_id == user_no_groups.id,
            StreamUser.stream_id == public_stream.id,
        )
        .first()
    )


@pytest.fixture()
def public_filter(public_group, public_stream):
    filter_ = FilterFactory(group=public_group, stream=public_stream)
    filter_id = filter_.id
    yield filter_
    FilterFactory.teardown(filter_id)


@pytest.fixture()
def public_filter2(public_group2, public_stream):
    filter_ = FilterFactory(group=public_group2, stream=public_stream)
    filter_id = filter_.id
    yield filter_
    FilterFactory.teardown(filter_id)


@pytest.fixture()
def public_ZTF20acgrjqm(public_group):
    obj = ObjFactory(groups=[public_group], ra=65.0630767, dec=82.5880983)
    DBSession().add(Source(obj_id=obj.id, group_id=public_group.id))
    DBSession().commit()
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def public_ZTF21aaeyldq(public_group):
    obj = ObjFactory(groups=[public_group], ra=123.813909, dec=-5.867007)
    DBSession().add(Source(obj_id=obj.id, group_id=public_group.id))
    DBSession().commit()
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def public_source(public_group):
    obj = ObjFactory(groups=[public_group])
    source = Source(obj_id=obj.id, group_id=public_group.id)
    DBSession.add(source)
    DBSession.commit()
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def public_source_two_groups(public_group, public_group2):
    obj = ObjFactory(groups=[public_group, public_group2])
    sources = []
    for group in [public_group, public_group2]:
        source = Source(obj_id=obj.id, group_id=group.id)
        sources.append(source)
        DBSession.add(source)
    DBSession.commit()
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def public_source_group2(public_group2):
    obj = ObjFactory(groups=[public_group2])
    source = Source(obj_id=obj.id, group_id=public_group2.id)
    DBSession.add(source)
    DBSession.commit()
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def public_source_no_data(public_group):
    obj = Obj(
        id=str(uuid.uuid4()),
        ra=0.0,
        dec=0.0,
        redshift=0.0,
    )
    DBSession.add(obj)
    DBSession().add(ThumbnailFactory(obj_id=obj.id, type="new"))
    DBSession().add(ThumbnailFactory(obj_id=obj.id, type="ps1"))
    source = Source(obj_id=obj.id, group_id=public_group.id)
    DBSession.add(source)
    DBSession.commit()
    obj_id = obj.id
    yield obj
    # If the obj wasn't deleted by the test using it, clean up
    DBSession().expire(obj)
    if DBSession().query(Obj).filter(Obj.id == obj_id).first():
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_candidate(public_filter, user):
    obj = ObjFactory(groups=[public_filter.group])
    candidate = Candidate(
        obj=obj,
        filter=public_filter,
        passed_at=datetime.utcnow() - timedelta(seconds=np.random.randint(0, 100)),
        uploader_id=user.id,
    )
    DBSession.add(candidate)
    DBSession.commit()
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def public_candidate_object(public_candidate):
    return public_candidate.candidates[0]


@pytest.fixture()
def public_source_object(public_source):
    return public_source.sources[0]


@pytest.fixture()
def public_candidate_two_groups(
    public_filter, public_filter2, public_group, public_group2, user
):
    obj = ObjFactory(groups=[public_group, public_group2])
    candidates = []
    for filter_ in [public_filter, public_filter2]:
        candidate = Candidate(
            obj=obj,
            filter=filter_,
            passed_at=datetime.utcnow() - timedelta(seconds=np.random.randint(0, 100)),
            uploader_id=user.id,
        )
        candidates.append(candidate)
        DBSession.add(candidate)
    DBSession.commit()
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def public_candidate2(public_filter, user):
    obj = ObjFactory(groups=[public_filter.group])
    DBSession.add(
        Candidate(
            obj=obj,
            filter=public_filter,
            passed_at=datetime.utcnow() - timedelta(seconds=np.random.randint(0, 100)),
            uploader_id=user.id,
        )
    )
    DBSession.commit()
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def public_obj(public_group):
    obj = ObjFactory(groups=[public_group])
    yield obj
    # If the obj wasn't deleted by the test using it, clean up
    ObjFactory.teardown(obj)


@pytest.fixture()
def red_transients_group(group_admin_user, view_only_user):
    group = GroupFactory(
        name=f'red transients-{uuid.uuid4().hex}',
        users=[group_admin_user, view_only_user],
    )
    group_id = group.id
    yield group
    GroupFactory.teardown(group_id)


@pytest.fixture()
def ztf_camera():
    instrument = InstrumentFactory()
    yield instrument
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def hst():
    telescope = TelescopeFactory(
        name=f'Hubble Space Telescope_{uuid.uuid4()}',
        nickname=f'HST_{uuid.uuid4()}',
        lat=0,
        lon=0,
        elevation=0,
        diameter=2.0,
        fixed_location=False,
    )
    telescope_id = telescope.id
    yield telescope
    TelescopeFactory.teardown(telescope_id)


@pytest.fixture()
def keck1_telescope():
    observer = astroplan.Observer.at_site('Keck')
    telescope = TelescopeFactory(
        name=f'Keck I Telescope_{uuid.uuid4()}',
        nickname=f'Keck1_{uuid.uuid4()}',
        lat=observer.location.lat.to('deg').value,
        lon=observer.location.lon.to('deg').value,
        elevation=observer.location.height.to('m').value,
        diameter=10.0,
    )
    telescope_id = telescope.id
    yield telescope
    TelescopeFactory.teardown(telescope_id)


@pytest.fixture()
def wise_18inch():
    telescope = TelescopeFactory(
        name=f'Wise 18-inch Telescope_{uuid.uuid4()}',
        nickname=f'Wise18_{uuid.uuid4()}',
        lat=34.763333,
        lon=30.595833,
        elevation=875,
        diameter=0.46,
    )
    telescope_id = telescope.id
    yield telescope
    TelescopeFactory.teardown(telescope_id)


@pytest.fixture()
def xinglong_216cm():
    telescope = TelescopeFactory(
        name=f'Xinglong 2.16m_{uuid.uuid4()}',
        nickname='XL216_{uuid.uuid4()}',
        lat=40.004463,
        lon=116.385556,
        elevation=950.0,
        diameter=2.16,
    )
    telescope_id = telescope.id
    yield telescope
    TelescopeFactory.teardown(telescope_id)


@pytest.fixture()
def p60_telescope():
    observer = astroplan.Observer.at_site('Palomar')
    telescope = TelescopeFactory(
        name=f'Palomar 60-inch telescope_{uuid.uuid4()}',
        nickname='p60_{uuid.uuid4()}',
        lat=observer.location.lat.to('deg').value,
        lon=observer.location.lon.to('deg').value,
        elevation=observer.location.height.to('m').value,
        diameter=1.6,
    )
    telescope_id = telescope.id
    yield telescope
    TelescopeFactory.teardown(telescope_id)


@pytest.fixture()
def lris(keck1_telescope):
    instrument = InstrumentFactory(
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
    yield instrument
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def sedm(p60_telescope):
    instrument = InstrumentFactory(
        name=f'SEDM_{uuid.uuid4()}',
        type='imaging spectrograph',
        telescope=p60_telescope,
        band='Optical',
        filters=['sdssu', 'sdssg', 'sdssr', 'sdssi'],
        api_classname='SEDMAPI',
        listener_classname='SEDMListener',
    )
    yield instrument
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def red_transients_run(user):
    run = ObservingRunFactory(owner=user)
    yield run
    ObservingRunFactory.teardown(run)


@pytest.fixture()
def lris_run_20201118(lris, public_group, super_admin_user):
    run = ObservingRunFactory(
        instrument=lris,
        group=public_group,
        calendar_date='2020-11-18',
        owner=super_admin_user,
    )
    yield run
    ObservingRunFactory.teardown(run)


@pytest.fixture()
def problematic_assignment(lris_run_20201118, public_ZTF20acgrjqm):
    assignment = ClassicalAssignmentFactory(
        run=lris_run_20201118,
        obj=public_ZTF20acgrjqm,
        requester=lris_run_20201118.owner,
        last_modified_by=lris_run_20201118.owner,
    )
    yield assignment
    ClassicalAssignmentFactory.teardown(assignment)


@pytest.fixture()
def public_assignment(red_transients_run, user, public_source):
    assignment = ClassicalAssignmentFactory(
        run=red_transients_run, obj=public_source, requester=user, last_modified_by=user
    )
    yield assignment
    ClassicalAssignmentFactory.teardown(assignment)


@pytest.fixture()
def private_source():
    obj = ObjFactory(groups=[])
    yield obj
    ObjFactory.teardown(obj)


@pytest.fixture()
def user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("Full user")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_stream2_only(public_group, public_stream2):
    user = UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("Full user")],
        streams=[public_stream2],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_group2(public_group2, public_stream):
    user = UserFactory(
        groups=[public_group2],
        roles=[models.Role.query.get("Full user")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def public_groupuser(public_group, user):
    user.groups.append(public_group)
    DBSession().commit()
    return (
        DBSession()
        .query(GroupUser)
        .filter(GroupUser.group_id == public_group.id, GroupUser.user_id == user.id)
        .first()
    )


@pytest.fixture()
def user2(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("Full user")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_no_groups(public_stream):
    user = UserFactory(
        roles=[models.Role.query.get("Full user")], streams=[public_stream]
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_no_groups_two_streams(public_stream, public_stream2):
    user = UserFactory(
        roles=[models.Role.query.get("Full user")],
        streams=[public_stream, public_stream2],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_no_groups_no_streams():
    user = UserFactory(roles=[models.Role.query.get("Full user")], streams=[])
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def view_only_token_no_groups(user_no_groups):
    token_id = create_token(ACLs=[], user_id=user_no_groups.id, name=str(uuid.uuid4()))
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def upload_data_token_stream2(user_stream2_only):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user_stream2_only.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def view_only_token_no_groups_no_streams(user_no_groups_no_streams):
    token_id = create_token(
        ACLs=[], user_id=user_no_groups_no_streams.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def upload_data_token_no_groups(user_no_groups):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user_no_groups.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def upload_data_token_no_groups_two_streams(user_no_groups_two_streams):
    token_id = create_token(
        ACLs=["Upload data"],
        user_id=user_no_groups_two_streams.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def upload_data_token_no_groups_no_streams(user_no_groups_no_streams):
    token_id = create_token(
        ACLs=["Upload data"],
        user_id=user_no_groups_no_streams.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def user_two_groups(public_group, public_group2, public_stream):
    user = UserFactory(
        groups=[public_group, public_group2],
        roles=[models.Role.query.get("Full user")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def view_only_user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("View only")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def view_only_user2(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("View only")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def group_admin_user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("Group admin")],
        streams=[public_stream],
    )
    user_id = user.id
    group_user = (
        DBSession()
        .query(GroupUser)
        .filter(GroupUser.group_id == public_group.id, GroupUser.user_id == user.id)
        .first()
    )
    group_user.admin = True
    DBSession().commit()
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def group_admin_user_two_groups(public_group, public_group2, public_stream):
    user = UserFactory(
        groups=[public_group, public_group2],
        roles=[models.Role.query.get("Group admin")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def super_admin_user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("Super admin")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def super_admin_user_group2(public_group2, public_stream):
    user = UserFactory(
        groups=[public_group2],
        roles=[models.Role.query.get("Super admin")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def super_admin_user_two_groups(public_group, public_group2, public_stream):
    user = UserFactory(
        groups=[public_group, public_group2],
        roles=[models.Role.query.get("Super admin")],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def view_only_token(user):
    token_id = create_token(ACLs=[], user_id=user.id, name=str(uuid.uuid4()))
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def view_only_token2(user2):
    token_id = create_token(ACLs=[], user_id=user2.id, name=str(uuid.uuid4()))
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def view_only_token_group2(user_group2):
    token_id = create_token(ACLs=[], user_id=user_group2.id, name=str(uuid.uuid4()))
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def upload_data_token_group2(user_group2):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user_group2.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def view_only_token_two_groups(user_two_groups):
    token_id = create_token(ACLs=[], user_id=user_two_groups.id, name=str(uuid.uuid4()))
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def manage_sources_token(group_admin_user):
    token_id = create_token(
        ACLs=["Manage sources"],
        user_id=group_admin_user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def manage_sources_token_two_groups(group_admin_user_two_groups):
    token_id = create_token(
        ACLs=["Manage sources"],
        user_id=group_admin_user_two_groups.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def upload_data_token(user):
    token_id = create_token(
        ACLs=["Upload data"], user_id=user.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def upload_data_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Upload data"],
        user_id=user_two_groups.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def manage_groups_token(super_admin_user):
    token_id = create_token(
        ACLs=["Manage groups", "Upload data"],
        user_id=super_admin_user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def group_admin_token(group_admin_user):
    token_id = create_token(
        ACLs=["Upload data"], user_id=group_admin_user.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def manage_users_token(super_admin_user):
    token_id = create_token(
        ACLs=["Manage users", "Upload data"],
        user_id=super_admin_user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def manage_users_token_group2(super_admin_user_group2):
    token_id = create_token(
        ACLs=["Manage users", "Upload data"],
        user_id=super_admin_user_group2.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def super_admin_token(super_admin_user):
    role = Role.query.get("Super admin")
    token_id = create_token(
        ACLs=[a.id for a in role.acls],
        user_id=super_admin_user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def super_admin_token_two_groups(super_admin_user_two_groups):
    role = Role.query.get("Super admin")
    token_id = create_token(
        ACLs=[a.id for a in role.acls],
        user_id=super_admin_user_two_groups.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def comment_token(user):
    token_id = create_token(ACLs=["Comment"], user_id=user.id, name=str(uuid.uuid4()))
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def annotation_token(user):
    token_id = create_token(ACLs=["Annotate"], user_id=user.id, name=str(uuid.uuid4()))
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def classification_token(user):
    token_id = create_token(ACLs=["Classify"], user_id=user.id, name=str(uuid.uuid4()))
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def classification_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Classify"], user_id=user_two_groups.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def taxonomy_token(user):
    token_id = create_token(
        ACLs=["Post taxonomy", "Delete taxonomy"],
        user_id=user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def taxonomy_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Post taxonomy", "Delete taxonomy"],
        user_id=user_two_groups.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def comment_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Comment"], user_id=user_two_groups.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def annotation_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Annotate"], user_id=user_two_groups.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def public_group_sedm_allocation(sedm, public_group):
    allocation = AllocationFactory(
        instrument=sedm,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )
    yield allocation
    AllocationFactory.teardown(allocation)


@pytest.fixture()
def public_group2_sedm_allocation(sedm, public_group2):
    allocation = AllocationFactory(
        instrument=sedm,
        group=public_group2,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )
    yield allocation
    AllocationFactory.teardown(allocation)


@pytest.fixture()
def public_source_followup_request(public_group_sedm_allocation, public_source, user):
    request = FollowupRequestFactory(
        obj=public_source,
        allocation=public_group_sedm_allocation,
        payload={
            'priority': "5",
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
        },
        requester=user,
        last_modified_by_id=user,
        target_groups=user.groups,
    )
    yield request
    FollowupRequestFactory.teardown(request)


@pytest.fixture()
def public_source_group2_followup_request(
    public_group2_sedm_allocation, public_source_group2, user_two_groups
):
    request = FollowupRequestFactory(
        obj=public_source_group2,
        allocation=public_group2_sedm_allocation,
        payload={
            'priority': "5",
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
        },
        requester=user_two_groups,
        last_modified_by=user_two_groups,
        target_groups=user_two_groups.groups,
    )
    yield request
    FollowupRequestFactory.teardown(request)


@pytest.fixture()
def sedm_listener_token(sedm, group_admin_user):
    token_id = create_token(
        ACLs=[sedm.listener_class.get_acl_id()],
        user_id=group_admin_user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def source_notification_user(public_group):
    user = UserFactory(
        contact_email="test_email@gmail.com",
        contact_phone="+12345678910",
        groups=[public_group],
        roles=[models.Role.query.get("Full user")],
        preferences={"allowEmailNotifications": True, "allowSMSNotifications": True},
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def source_notification_user_token(source_notification_user):
    token_id = create_token(
        ACLs=[],
        user_id=source_notification_user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def public_taxonomy(public_group):
    taxonomy = TaxonomyFactory(groups=[public_group])
    taxonomy_id = taxonomy.id
    yield taxonomy
    TaxonomyFactory.teardown(taxonomy_id)


@pytest.fixture()
def public_group_taxonomy(public_taxonomy):
    return (
        DBSession()
        .query(GroupTaxonomy)
        .filter(
            GroupTaxonomy.group_id == public_taxonomy.groups[0].id,
            GroupTaxonomy.taxonomie_id == public_taxonomy.id,
        )
        .first()
    )


@pytest.fixture()
def public_comment(user_no_groups, public_source, public_group):
    comment = CommentFactory(
        obj=public_source, groups=[public_group], author=user_no_groups
    )
    yield comment
    CommentFactory.teardown(comment)


@pytest.fixture()
def public_groupcomment(public_comment):
    return (
        DBSession()
        .query(GroupComment)
        .filter(
            GroupComment.group_id == public_comment.groups[0].id,
            GroupComment.comment_id == public_comment.id,
        )
        .first()
    )


@pytest.fixture()
def public_annotation(user_no_groups, public_source, public_group):
    annotation = AnnotationFactory(
        obj=public_source, groups=[public_group], author=user_no_groups
    )
    yield annotation
    AnnotationFactory.teardown(annotation)


@pytest.fixture()
def public_groupannotation(public_annotation):
    return (
        DBSession()
        .query(GroupAnnotation)
        .filter(
            GroupAnnotation.group_id == public_annotation.groups[0].id,
            GroupAnnotation.annotation_id == public_annotation.id,
        )
        .first()
    )


@pytest.fixture()
def public_classification(
    public_taxonomy, user_two_groups, public_group, public_source
):
    classification = ClassificationFactory(
        obj=public_source,
        groups=[public_group],
        author=user_two_groups,
        taxonomy=public_taxonomy,
    )
    yield classification
    ClassificationFactory.teardown(classification)


@pytest.fixture()
def public_groupclassification(public_classification):
    return (
        DBSession()
        .query(GroupClassification)
        .filter(
            GroupClassification.group_id == public_classification.groups[0].id,
            GroupClassification.classification_id == public_classification.id,
        )
        .first()
    )


@pytest.fixture()
def public_source_photometry_point(public_source):
    return public_source.photometry[0]


@pytest.fixture()
def public_source_spectrum(public_source):
    return public_source.spectra[0]


@pytest.fixture()
def public_source_groupphotometry(public_source_photometry_point):
    return (
        DBSession()
        .query(GroupPhotometry)
        .filter(
            GroupPhotometry.group_id == public_source_photometry_point.groups[0].id,
            GroupPhotometry.photometr_id == public_source_photometry_point.id,
        )
        .first()
    )


@pytest.fixture()
def public_source_groupspectrum(public_source_spectrum):
    return (
        DBSession()
        .query(GroupSpectrum)
        .filter(
            GroupSpectrum.group_id == public_source_spectrum.groups[0].id,
            GroupSpectrum.spectr_id == public_source_spectrum.id,
        )
        .first()
    )


@pytest.fixture()
def public_source_followup_request_target_group(public_source_followup_request):
    return (
        DBSession()
        .query(FollowupRequestTargetGroup)
        .filter(
            FollowupRequestTargetGroup.followuprequest_id
            == public_source_followup_request.id,
            FollowupRequestTargetGroup.group_id
            == public_source_followup_request.target_groups[0].id,
        )
        .first()
    )


@pytest.fixture()
def public_thumbnail(public_source):
    return (
        DBSession()
        .query(Thumbnail)
        .filter(Thumbnail.obj_id == public_source.id)
        .order_by(Thumbnail.id.desc())
        .first()
    )


@pytest.fixture()
def invitation(user):
    invitation = InvitationFactory(invited_by=user)
    yield invitation
    InvitationFactory.teardown(invitation)


@pytest.fixture()
def public_source_notification(source_notification_user, public_source):
    notification = NotificationFactory(
        sent_by=source_notification_user, source=public_source
    )
    yield notification
    NotificationFactory.teardown(notification)


@pytest.fixture()
def user_notification(user):
    user_notification = UserNotificationFactory(user=user)
    yield user_notification
    UserNotificationFactory.teardown(user_notification)
