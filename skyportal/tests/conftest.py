"""Test fixture configuration."""

import base64
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import astroplan
import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa

from baselayer.app import models
from skyportal.model_util import create_token, delete_token
from skyportal.models import (
    Candidate,
    DBSession,
    FollowupRequestTargetGroup,
    GroupAnnotation,
    GroupClassification,
    GroupComment,
    GroupPhotometry,
    GroupSpectrum,
    GroupStream,
    GroupTaxonomy,
    GroupUser,
    Obj,
    PhotometricSeries,
    Source,
    StreamUser,
    Thumbnail,
    User,
)
from skyportal.tests.fixtures import (
    TMP_DIR,  # noqa: F401
    AllocationFactory,
    AnnotationFactory,
    ClassicalAssignmentFactory,
    ClassificationFactory,
    CommentFactory,
    CommentOnGCNFactory,
    FilterFactory,
    FollowupRequestFactory,
    GcnEventFactory,
    GroupFactory,
    InstrumentFactory,
    InvitationFactory,
    NotificationFactory,
    ObjFactory,
    ObservingRunFactory,
    StreamFactory,
    TaxonomyFactory,
    TelescopeFactory,
    ThumbnailFactory,
    UserFactory,
    UserNotificationFactory,
)
from skyportal.tests.test_util import driver  # noqa: F401

if shutil.which("geckodriver") is None:
    raise RuntimeError(
        "Geckodriver needs to be installed for browser automation.\n"
        "See https://github.com/mozilla/geckodriver/releases"
    )


# Add a "test factory" User so that all factory-generated comments have a
# proper author, if it doesn't already exist (the user may already be in
# there if running the test server and running tests individually)
if (
    not DBSession()
    .execute(sa.select(User).filter(User.username == "test factory"))
    .scalar()
):
    DBSession.add(User(username="test factory"))
    DBSession.commit()

# Also add the test driver user (testuser-cesium-ml-org) if needed so that the driver
# fixture has a user to login as (without needing an invitation token).
# With invitations enabled on the test configs, the driver fails to login properly
# without this user because the authenticator looks for the user or an
# invitation token when neither exists initially on fresh test databases.
if (
    not DBSession()
    .execute(sa.select(User).filter(User.username == "testuser-cesium-ml-org"))
    .scalar()
):
    DBSession.add(
        User(username="testuser-cesium-ml-org", oauth_uid="testuser@cesium-ml.org")
    )
    DBSession.commit()


def pytest_runtest_setup(item):
    # Print timestamp when running each test
    print(datetime.now().strftime("[%H:%M:%S] "), end="")


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
    if "driver" in request.node.funcargs:
        testuser = (
            DBSession()
            .execute(sa.select(User).filter(User.username == "testuser-cesium-ml-org"))
            .scalars()
            .first()
        )
        webdriver = request.node.funcargs["driver"]
        webdriver.get(f"/become_user/{testuser.id}")


# check if a test has failed
@pytest.fixture(scope="function", autouse=True)
def test_failed_check(request):
    gecko = Path("geckodriver.log")
    gecko.touch(exist_ok=True)

    # get the number of bytes in the file currently
    log_bytes = os.path.getsize(gecko)

    # add a separator to the geckodriver logs
    with open(gecko, "a") as f:
        f.write(f"BEGIN {request.node.nodeid}\n")

    yield
    # request.node is an "item" because we use the default
    # "function" scope

    # add a separator to the geckodriver logs
    with open(gecko, "a") as f:
        f.write(f"END {request.node.nodeid}\n")

    if request.node.rep_call.failed and "driver" in request.node.funcargs:
        webdriver = request.node.funcargs["driver"]
        take_screenshot_and_page_source(webdriver, request.node.nodeid)

    # delete the interstitial data from the geckodriver log by
    # truncating the file back to its original number of bytes
    with open(gecko, "a") as f:
        f.truncate(log_bytes)


# make a screenshot with a name of the test, date and time.
# also save the page HTML.
def take_screenshot_and_page_source(webdriver, nodeid):
    file_name = f"{nodeid}_{datetime.today().strftime('%Y-%m-%d_%H:%M')}.png".replace(
        "/", "_"
    ).replace(":", "_")
    file_name = os.path.join(os.path.dirname(__file__), "../../test-results", file_name)
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)

    webdriver.save_screenshot(file_name)
    with open(file_name.replace("png", "html"), "w") as f:
        f.write(webdriver.page_source)

    file_name = (
        f"{nodeid}_{datetime.today().strftime('%Y-%m-%d_%H:%M')}.console.log".replace(
            "/", "_"
        ).replace(":", "_")
    )
    file_name = os.path.join(
        os.path.dirname(__file__), "../../webdriver-console", file_name
    )
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)

    with open(file_name, "w") as f, open("geckodriver.log") as gl:
        lines = gl.readlines()
        revlines = list(reversed(lines))
        istart = revlines.index(f"BEGIN {nodeid}\n")
        iend = revlines.index(f"END {nodeid}\n")
        f.write("\n".join(list(reversed(revlines[iend : (istart + 1)]))))  # noqa: E203


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
        .execute(
            sa.select(GroupStream).filter(
                GroupStream.group_id == public_group.id,
                GroupStream.stream_id == public_group.streams[0].id,
            )
        )
        .scalars()
        .first()
    )


@pytest.fixture()
def public_streamuser(public_stream, user):
    return (
        DBSession()
        .execute(
            sa.select(StreamUser).filter(
                StreamUser.user_id == user.id, StreamUser.stream_id == public_stream.id
            )
        )
        .scalars()
        .first()
    )


@pytest.fixture()
def public_streamuser_no_groups(public_stream, user_no_groups):
    return (
        DBSession()
        .execute(
            sa.select(StreamUser).filter(
                StreamUser.user_id == user_no_groups.id,
                StreamUser.stream_id == public_stream.id,
            )
        )
        .scalars()
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
def public_ZTFe028h94k(public_group):
    obj = ObjFactory(groups=[public_group], ra=229.9620403, dec=34.8442757)
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
    if DBSession().execute(sa.select(Obj).filter(Obj.id == obj_id)).scalars().first():
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
        name=f"red transients-{uuid.uuid4().hex}",
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
        name=f"Hubble Space Telescope_{uuid.uuid4()}",
        nickname=f"HST_{uuid.uuid4()}",
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
    observer = astroplan.Observer.at_site("Keck")
    telescope = TelescopeFactory(
        name=f"Keck I Telescope_{uuid.uuid4()}",
        nickname=f"Keck1_{uuid.uuid4()}",
        lat=observer.location.lat.to("deg").value,
        lon=observer.location.lon.to("deg").value,
        elevation=observer.location.height.to("m").value,
        diameter=10.0,
    )
    telescope_id = telescope.id
    yield telescope
    TelescopeFactory.teardown(telescope_id)


@pytest.fixture()
def wise_18inch():
    telescope = TelescopeFactory(
        name=f"Wise 18-inch Telescope_{uuid.uuid4()}",
        nickname=f"Wise18_{uuid.uuid4()}",
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
        name=f"Xinglong 2.16m_{uuid.uuid4()}",
        nickname="XL216_{uuid.uuid4()}",
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
    observer = astroplan.Observer.at_site("Palomar")
    telescope = TelescopeFactory(
        name=f"Palomar 60-inch telescope_{uuid.uuid4()}",
        nickname=f"p60_{uuid.uuid4()}",
        lat=observer.location.lat.to("deg").value,
        lon=observer.location.lon.to("deg").value,
        elevation=observer.location.height.to("m").value,
        diameter=1.6,
    )
    telescope_id = telescope.id
    yield telescope
    TelescopeFactory.teardown(telescope_id)


@pytest.fixture()
def lris(keck1_telescope):
    instrument = InstrumentFactory(
        name=f"LRIS_{uuid.uuid4()}",
        type="imaging spectrograph",
        telescope=keck1_telescope,
        band="Optical",
        filters=[
            "sdssu",
            "sdssg",
            "sdssr",
            "sdssi",
            "sdssz",
            "bessellux",
            "bessellv",
            "bessellb",
            "bessellr",
            "besselli",
        ],
    )
    yield instrument
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def sedm(p60_telescope):
    instrument = InstrumentFactory(
        name=f"SEDM_{uuid.uuid4()}",
        type="imaging spectrograph",
        telescope=p60_telescope,
        band="Optical",
        filters=["sdssu", "sdssg", "sdssr", "sdssi"],
        api_classname="SEDMAPI",
        listener_classname="SEDMListener",
    )
    yield instrument
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def generic_instrument(p60_telescope):
    instrument = InstrumentFactory(
        name=f"GenericInstrument_{uuid.uuid4()}",
        type="imaging spectrograph",
        telescope=p60_telescope,
        band="Optical",
        filters=["sdssu", "sdssg", "sdssr", "sdssi"],
        api_classname="GENERICAPI",
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
        calendar_date="2020-11-18",
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
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_stream2_only(public_group, public_stream2):
    user = UserFactory(
        groups=[public_group],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
        streams=[public_stream2],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_group2(public_group2, public_stream):
    user = UserFactory(
        groups=[public_group2],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def public_groupuser(public_group, user):
    if public_group not in user.groups:
        user.groups.append(public_group)
    DBSession().commit()
    return (
        DBSession()
        .execute(
            sa.select(GroupUser).filter(
                GroupUser.group_id == public_group.id, GroupUser.user_id == user.id
            )
        )
        .scalars()
        .first()
    )


@pytest.fixture()
def user2(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_no_groups(public_stream):
    user = UserFactory(
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_no_groups_two_streams(public_stream, public_stream2):
    user = UserFactory(
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
        streams=[public_stream, public_stream2],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def user_no_groups_no_streams():
    user = UserFactory(
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
        streams=[],
    )
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
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def view_only_user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "View only"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def view_only_user2(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "View only"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def group_admin_user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Group admin"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    group_user = (
        DBSession()
        .execute(
            sa.select(GroupUser).filter(
                GroupUser.group_id == public_group.id, GroupUser.user_id == user.id
            )
        )
        .scalars()
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
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Group admin"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def super_admin_user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Super admin"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def super_admin_user_group2(public_group2, public_stream):
    user = UserFactory(
        groups=[public_group2],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Super admin"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def super_admin_user_two_groups(public_group, public_group2, public_stream):
    user = UserFactory(
        groups=[public_group, public_group2],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Super admin"))
            .scalars()
            .first()
        ],
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
def observing_run_token(user):
    token_id = create_token(
        ACLs=["Manage observing runs"], user_id=user.id, name=str(uuid.uuid4())
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
    role = (
        DBSession()
        .execute(sa.select(models.Role).filter(models.Role.id == "Super admin"))
        .scalars()
        .first()
    )
    token_id = create_token(
        ACLs=[a.id for a in role.acls],
        user_id=super_admin_user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def super_admin_token_two_groups(super_admin_user_two_groups):
    role = (
        DBSession()
        .execute(sa.select(models.Role).filter(models.Role.id == "Super admin"))
        .scalars()
        .first()
    )
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
        validity_ranges=[
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
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
        validity_ranges=[
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
    )
    yield allocation
    AllocationFactory.teardown(allocation)


@pytest.fixture()
def public_group_generic_allocation(generic_instrument, public_group):
    allocation = AllocationFactory(
        instrument=generic_instrument,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
        validity_ranges=[
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
    )
    yield allocation
    AllocationFactory.teardown(allocation)


@pytest.fixture()
def public_source_followup_request(public_group_sedm_allocation, public_source, user):
    request = FollowupRequestFactory(
        obj=public_source,
        allocation=public_group_sedm_allocation,
        payload={
            "priority": "5",
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
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
            "priority": "5",
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
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
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
            .scalars()
            .first()
        ],
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
        .execute(
            sa.select(GroupTaxonomy).filter(
                GroupTaxonomy.group_id == public_taxonomy.groups[0].id,
                GroupTaxonomy.taxonomie_id == public_taxonomy.id,
            )
        )
        .scalars()
        .first()
    )


@pytest.fixture()
def gcn_GRB180116A(user_no_groups):
    dateobs = datetime.strptime("2018-01-16 00:36:53", "%Y-%m-%d %H:%M:%S")
    notice_dict = {
        "notice_type": "Test",
        "notice_format": "Test",
        "stream": "Test",
        "dateobs": dateobs,
        "date": "2018-01-16 00:36:53",
        "content": bytes(1024),
        "has_localization": True,
        "localization_ingested": True,
    }

    localization_dict = {
        "localization_name": "Test",
        "localization_data_path": "data/localization_GRB180116A.parquet",
        "localization_tiles_data_path": "data/localizationtiles_GRB180116A.parquet",
        "properties": {"test": "test"},
        "tags": ["Test"],
    }

    gcnevent = GcnEventFactory(
        dateobs=dateobs,
        trigger_id="537755817",
        aliases=["FERMI#bn180116026"],
        gcn_notices=[notice_dict],
        properties={"test": "test"},
        localizations=[localization_dict],
    )
    yield gcnevent
    GcnEventFactory.teardown(gcnevent)


@pytest.fixture()
def gcn_GW190814(user_no_groups):
    dateobs = datetime.strptime("2019-08-14 21:10:39", "%Y-%m-%d %H:%M:%S")
    notice_dict = {
        "notice_type": "Test",
        "notice_format": "Test",
        "stream": "Test",
        "dateobs": dateobs,
        "date": "2019-08-14 21:10:39",
        "content": bytes(1024),
        "has_localization": True,
        "localization_ingested": True,
    }

    localization_dict = {
        "localization_name": "LALInference.v1.fits.gz",
        "localization_data_path": "data/localization_GW190814.parquet",
        "localization_tiles_data_path": "data/localizationtiles_GW190814.parquet",
        "properties": {"test": "test"},
        "tags": ["Test"],
    }

    gcnevent = GcnEventFactory(
        dateobs=dateobs,
        aliases=["LVC#S190814bv"],
        gcn_notices=[notice_dict],
        properties={"test": "test"},
        localizations=[localization_dict],
    )
    yield gcnevent
    GcnEventFactory.teardown(gcnevent)


@pytest.fixture()
def gcn_GW190425(user_no_groups):
    dateobs = datetime.strptime("2019-04-25 08:18:05", "%Y-%m-%d %H:%M:%S")
    notice_dict = {
        "notice_type": "Test",
        "notice_format": "Test",
        "stream": "Test",
        "dateobs": dateobs,
        "date": "2019-04-25 08:18:05",
        "content": bytes(1024),
        "has_localization": True,
        "localization_ingested": True,
    }

    localization_dict = {
        "localization_name": "bayestar.fits.gz",
        "localization_data_path": "data/localization_GW190425.parquet",
        "localization_tiles_data_path": "data/localizationtiles_GW190425.parquet",
        "properties": {"test": "test"},
        "tags": ["Test"],
    }

    gcnevent = GcnEventFactory(
        dateobs=dateobs,
        aliases=["LVC#S190425z"],
        gcn_notices=[notice_dict],
        properties={"test": "test"},
        localizations=[localization_dict],
    )
    yield gcnevent
    GcnEventFactory.teardown(gcnevent)


@pytest.fixture()
def public_comment(user_no_groups, public_source, public_group):
    comment = CommentFactory(
        obj=public_source, groups=[public_group], author=user_no_groups
    )
    yield comment
    CommentFactory.teardown(comment)


@pytest.fixture()
def public_comment_on_gcn(gcn, public_group):
    comment = CommentOnGCNFactory(gcn=gcn, groups=[public_group])
    yield comment
    CommentOnGCNFactory.teardown(comment)


@pytest.fixture()
def public_groupcomment(public_comment):
    return (
        DBSession()
        .execute(
            sa.select(GroupComment).filter(
                GroupComment.group_id == public_comment.groups[0].id,
                GroupComment.comment_id == public_comment.id,
            )
        )
        .scalars()
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
        .execute(
            sa.select(GroupAnnotation).filter(
                GroupAnnotation.group_id == public_annotation.groups[0].id,
                GroupAnnotation.annotation_id == public_annotation.id,
            )
        )
        .scalars()
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
        .execute(
            sa.select(GroupClassification).filter(
                GroupClassification.group_id == public_classification.groups[0].id,
                GroupClassification.classification_id == public_classification.id,
            )
        )
        .scalars()
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
        .execute(
            sa.select(GroupPhotometry).filter(
                GroupPhotometry.group_id == public_source_photometry_point.groups[0].id,
                GroupPhotometry.photometr_id == public_source_photometry_point.id,
            )
        )
        .scalars()
        .first()
    )


@pytest.fixture()
def public_source_groupspectrum(public_source_spectrum):
    return (
        DBSession()
        .execute(
            sa.select(GroupSpectrum).filter(
                GroupSpectrum.group_id == public_source_spectrum.groups[0].id,
                GroupSpectrum.spectr_id == public_source_spectrum.id,
            )
        )
        .scalars()
        .first()
    )


@pytest.fixture()
def public_source_followup_request_target_group(public_source_followup_request):
    return (
        DBSession()
        .execute(
            sa.select(FollowupRequestTargetGroup).filter(
                FollowupRequestTargetGroup.followuprequest_id
                == public_source_followup_request.id,
                FollowupRequestTargetGroup.group_id
                == public_source_followup_request.target_groups[0].id,
            )
        )
        .scalars()
        .first()
    )


@pytest.fixture()
def public_thumbnail(public_source):
    return (
        DBSession()
        .execute(
            sa.select(Thumbnail)
            .filter(Thumbnail.obj_id == public_source.id)
            .order_by(Thumbnail.id.desc())
        )
        .scalars()
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


@pytest.fixture()
def shift_admin(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "Group admin"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
    )
    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def shift_user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[
            DBSession()
            .execute(sa.select(models.Role).filter(models.Role.id == "View only"))
            .scalars()
            .first()
        ],
        streams=[public_stream],
        acls=[
            DBSession()
            .execute(sa.select(models.ACL).filter(models.ACL.id == "Manage shifts"))
            .scalars()
            .first()
        ],
    )

    user_id = user.id
    yield user
    UserFactory.teardown(user_id)


@pytest.fixture()
def analysis_service_token(user):
    token_id = create_token(
        ACLs=["Manage Analysis Services"],
        user_id=user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def analysis_service_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Manage Analysis Services"],
        user_id=user_two_groups.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def analysis_token(user):
    token_id = create_token(
        ACLs=["Run Analyses"],
        user_id=user.id,
        name=str(uuid.uuid4()),
    )
    yield token_id
    delete_token(token_id)


@pytest.fixture()
def phot_series_maker():
    def _phot_series_maker(
        number=20,
        format="dict",
        use_mags=True,
        ra=None,
        dec=None,
        exptime=30,
        filter=None,
        extra_columns=None,
    ):
        flux = np.random.uniform(15, 16, number)
        mjds = np.sort(np.random.uniform(59000, 60000, number))
        if ra is None:
            ra = np.random.uniform(0, 360)
        if dec is None:
            dec = np.random.uniform(-90, 90)
        if filter is None:
            filter = np.random.choice(["ztfg", "ztfr", "ztfi"])

        if use_mags:
            data = {"mag": flux}
        else:
            data = {"flux": flux}

        data["mjd"] = mjds

        if extra_columns is None:
            extra_columns = []

        if "ra" in extra_columns:
            data["ra"] = np.mod(np.random.normal(ra, 0.001, number), 360)
        if "dec" in extra_columns:
            data["dec"] = np.random.normal(dec, 0.001, number)
            data["dec"] = np.maximum(data["dec"], -90)
            data["dec"] = np.minimum(data["dec"], 90)
        if "exp_time" in extra_columns:
            data["exp_time"] = np.array([exptime] * number)
        if "filter" in extra_columns:
            data["filter"] = np.array([filter] * number)

        for name in extra_columns:
            if name not in ["ra", "dec", "exp_time", "filter"]:
                data[name] = np.random.uniform(0, 1, number)

        if format == "dict":
            for k, v in data.items():
                data[k] = v.tolist()
        elif format == "pandas":
            data = pd.DataFrame(data)
        elif format == "bytes":
            # this store should work without writing to disk
            # if you open a regular store you'd just need
            # to delete the file at the end
            with pd.HDFStore(
                "test_file.h5",
                mode="w",
                driver="H5FD_CORE",
                driver_core_backing_store=0,
            ) as store:
                store.put(
                    "phot_series",
                    pd.DataFrame(data),
                    format="table",
                    index=None,
                    track_times=False,
                )
                data = store._handle.get_file_image()
                data = base64.b64encode(data)

            # should not be any file like this
            assert not os.path.isfile("test_file.h5")

        return data

    return _phot_series_maker


@pytest.fixture()
def photometric_series(
    user, public_source, public_group, ztf_camera, phot_series_maker
):
    df = phot_series_maker(format="pandas", number=20)
    data = {
        "obj_id": public_source.id,
        "data": df,
        "instrument_id": ztf_camera.id,
        "owner_id": user.id,
        "series_name": "test_series1",
        "series_obj_id": str(np.random.randint(0, 1e6)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 30.0,
        "filter": "ztfg",
        "magref": 18.1,
        "group_ids": [public_group.id, user.single_user_group.id],
        "stream_ids": [],
        "origin": uuid.uuid4().hex,
        "channel": np.random.choice(["A", "B"]),
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()

    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        raise e

    yield ps

    # tear down
    filename = ps.filename
    DBSession().delete(ps)
    DBSession().commit()
    if os.path.isfile(filename):
        os.remove(filename)


@pytest.fixture()
def photometric_series2(
    user, public_source_group2, public_group2, ztf_camera, phot_series_maker
):
    df = phot_series_maker(format="pandas", number=19)
    data = {
        "obj_id": public_source_group2.id,
        "data": df,
        "instrument_id": ztf_camera.id,
        "owner_id": user.id,
        "series_name": "test_series2",
        "series_obj_id": str(np.random.randint(0, 1e6)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 35.0,
        "filter": "ztfr",
        "magref": 19.2,
        "group_ids": [public_group2.id, user.single_user_group.id],
        "stream_ids": [],
        "origin": uuid.uuid4().hex,
        "channel": "A",
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()

    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        raise e

    yield ps

    # tear down
    filename = ps.filename
    DBSession().delete(ps)
    DBSession().commit()
    if os.path.isfile(filename):
        os.remove(filename)


@pytest.fixture()
def photometric_series3(
    user, public_source_two_groups, public_group, public_group2, sedm, phot_series_maker
):
    df = phot_series_maker(format="pandas", number=18)
    data = {
        "obj_id": public_source_two_groups.id,
        "data": df,
        "instrument_id": sedm.id,
        "owner_id": user.id,
        "series_name": "test_series3",
        "series_obj_id": str(np.random.randint(0, 1e6)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 25.0,
        "filter": "ztfi",
        "magref": 20.3,
        "group_ids": [public_group.id, public_group2.id, user.single_user_group.id],
        "stream_ids": [],
        "origin": uuid.uuid4().hex,
        "channel": "B",
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()

    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        raise e

    yield ps

    # tear down
    filename = ps.filename
    DBSession().delete(ps)
    DBSession().commit()
    if os.path.isfile(filename):
        os.remove(filename)


@pytest.fixture()
def photometric_series_low_flux(
    user, public_source, public_group, public_group2, ztf_camera, phot_series_maker
):
    df = phot_series_maker(number=100, use_mags=False, format="pandas")
    df["flux"] = np.random.normal(100, 10, 100)

    data = {
        "obj_id": public_source.id,
        "data": df,
        "instrument_id": ztf_camera.id,
        "owner_id": user.id,
        "series_name": "test_series",
        "series_obj_id": str(np.random.randint(0, 1e6)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 25.0,
        "filter": "ztfi",
        "group_ids": [public_group.id, public_group2.id, user.single_user_group.id],
        "stream_ids": [],
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()

    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        raise e

    yield ps

    # tear down
    filename = ps.filename
    DBSession().delete(ps)
    DBSession().commit()
    if os.path.isfile(filename):
        os.remove(filename)


@pytest.fixture()
def photometric_series_high_flux(
    user, public_source, public_group, public_group2, ztf_camera, phot_series_maker
):
    df = phot_series_maker(number=100, use_mags=False, format="pandas")
    df["flux"] = np.random.normal(10000, 100, 100)

    data = {
        "obj_id": public_source.id,
        "data": df,
        "instrument_id": ztf_camera.id,
        "owner_id": user.id,
        "series_name": "test_series",
        "series_obj_id": str(np.random.randint(0, 1e6)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 25.0,
        "filter": "ztfi",
        "group_ids": [public_group.id, public_group2.id, user.single_user_group.id],
        "stream_ids": [],
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()

    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        raise e

    yield ps

    # tear down
    filename = ps.filename
    DBSession().delete(ps)
    DBSession().commit()
    if os.path.isfile(filename):
        os.remove(filename)


@pytest.fixture()
def photometric_series_low_flux_with_outliers(
    user, public_source, public_group, public_group2, ztf_camera, phot_series_maker
):
    df = phot_series_maker(number=100, use_mags=False, format="pandas")
    df["flux"] = np.random.normal(100, 10, 100)

    # add some outliers
    df.loc[5, "flux"] = 5000
    df.loc[50, "flux"] = 6000
    df.loc[95, "flux"] = 0

    data = {
        "obj_id": public_source.id,
        "data": df,
        "instrument_id": ztf_camera.id,
        "owner_id": user.id,
        "series_name": "test_series_outliers",
        "series_obj_id": str(np.random.randint(0, 1e6)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 25.0,
        "filter": "ztfi",
        "group_ids": [public_group.id, public_group2.id, user.single_user_group.id],
        "stream_ids": [],
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()

    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        raise e

    yield ps

    # tear down
    filename = ps.filename
    DBSession().delete(ps)
    DBSession().commit()
    if os.path.isfile(filename):
        os.remove(filename)


@pytest.fixture()
def photometric_series_undetected(
    user, public_source, public_group, public_group2, ztf_camera, phot_series_maker
):
    df = phot_series_maker(number=100, use_mags=False, format="pandas")
    df["flux"] = np.random.normal(-50, 50, 100)

    data = {
        "obj_id": public_source.id,
        "data": df,
        "instrument_id": ztf_camera.id,
        "owner_id": user.id,
        "series_name": "test_series",
        "series_obj_id": str(np.random.randint(0, 1e6)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 25.0,
        "filter": "ztfi",
        "group_ids": [public_group.id, public_group2.id, user.single_user_group.id],
        "stream_ids": [],
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()

    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        raise e

    yield ps

    # tear down
    filename = ps.filename
    DBSession().delete(ps)
    DBSession().commit()
    if os.path.isfile(filename):
        os.remove(filename)
