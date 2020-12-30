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
from skyportal.model_util import create_token
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
)
from skyportal.tests.fixtures import TMP_DIR  # noqa: F401

# Add a "test factory" User so that all factory-generated comments have a
# proper author, if it doesn't already exist (the user may already be in
# there if running the test server and running tests individually)
if not DBSession.query(User).filter(User.username == "test factory").scalar():
    DBSession.add(User(username="test factory"))
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

    file_name = f'{nodeid}_{datetime.today().strftime("%Y-%m-%d_%H:%M")}.console.log'.replace(
        "/", "_"
    ).replace(
        ":", "_"
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
    return StreamFactory()


@pytest.fixture()
def public_stream2():
    return StreamFactory()


@pytest.fixture()
def stream_with_users(super_admin_user, group_admin_user, user, view_only_user):
    return StreamFactory(
        users=[super_admin_user, group_admin_user, user, view_only_user]
    )


@pytest.fixture()
def public_group(public_stream):
    return GroupFactory(streams=[public_stream])


@pytest.fixture()
def public_group2(public_stream2):
    return GroupFactory(streams=[public_stream2])


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
def public_filter(public_group, public_stream):
    return FilterFactory(group=public_group, stream=public_stream)


@pytest.fixture()
def public_filter2(public_group2, public_stream):
    return FilterFactory(group=public_group2, stream=public_stream)


@pytest.fixture()
def public_ZTF20acgrjqm(public_group):
    obj = ObjFactory(groups=[public_group], ra=65.0630767, dec=82.5880983)
    DBSession().add(Source(obj_id=obj.id, group_id=public_group.id))
    DBSession().commit()
    return obj


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
def public_candidate(public_filter, user):
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
    return obj


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
    DBSession.add(
        Candidate(
            obj=obj,
            filter=public_filter,
            passed_at=datetime.utcnow() - timedelta(seconds=np.random.randint(0, 100)),
            uploader_id=user.id,
        )
    )
    DBSession.add(
        Candidate(
            obj=obj,
            filter=public_filter2,
            passed_at=datetime.utcnow() - timedelta(seconds=np.random.randint(0, 100)),
            uploader_id=user.id,
        )
    )
    DBSession.commit()
    return obj


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
    return obj


@pytest.fixture()
def public_obj(public_group):
    return ObjFactory(groups=[public_group])


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
def hst():
    return TelescopeFactory(
        name=f'Hubble Space Telescope_{uuid.uuid4()}',
        nickname=f'HST_{uuid.uuid4()}',
        lat=0,
        lon=0,
        elevation=0,
        diameter=2.0,
        fixed_location=False,
    )


@pytest.fixture()
def keck1_telescope():
    observer = astroplan.Observer.at_site('Keck')
    return TelescopeFactory(
        name=f'Keck I Telescope_{uuid.uuid4()}',
        nickname=f'Keck1_{uuid.uuid4()}',
        lat=observer.location.lat.to('deg').value,
        lon=observer.location.lon.to('deg').value,
        elevation=observer.location.height.to('m').value,
        diameter=10.0,
    )


@pytest.fixture()
def wise_18inch():
    return TelescopeFactory(
        name=f'Wise 18-inch Telescope_{uuid.uuid4()}',
        nickname=f'Wise18_{uuid.uuid4()}',
        lat=34.763333,
        lon=30.595833,
        elevation=875,
        diameter=0.46,
    )


@pytest.fixture()
def xinglong_216cm():
    return TelescopeFactory(
        name=f'Xinglong 2.16m_{uuid.uuid4()}',
        nickname='XL216_{uuid.uuid4()}',
        lat=40.004463,
        lon=116.385556,
        elevation=950.0,
        diameter=2.16,
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
def lris_run_20201118(lris, public_group, super_admin_user):
    return ObservingRunFactory(
        instrument=lris,
        group=public_group,
        calendar_date='2020-11-18',
        owner=super_admin_user,
    )


@pytest.fixture()
def problematic_assignment(lris_run_20201118, public_ZTF20acgrjqm):
    return ClassicalAssignmentFactory(
        run=lris_run_20201118,
        obj=public_ZTF20acgrjqm,
        requester=lris_run_20201118.owner,
        last_modified_by=lris_run_20201118.owner,
    )


@pytest.fixture()
def private_source():
    return ObjFactory(groups=[])


@pytest.fixture()
def user(public_group, public_stream):
    return UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("Full user")],
        streams=[public_stream],
    )


@pytest.fixture()
def user_group2(public_group2, public_stream):
    return UserFactory(
        groups=[public_group2],
        roles=[models.Role.query.get("Full user")],
        streams=[public_stream],
    )


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
def user2(public_group):
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
def view_only_user2(public_group):
    return UserFactory(
        groups=[public_group], roles=[models.Role.query.get("View only")]
    )


@pytest.fixture()
def group_admin_user(public_group, public_stream):
    user = UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("Group admin")],
        streams=[public_stream],
    )
    group_user = (
        DBSession()
        .query(GroupUser)
        .filter(GroupUser.group_id == public_group.id, GroupUser.user_id == user.id)
        .first()
    )
    group_user.admin = True
    DBSession().commit()
    return user


@pytest.fixture()
def group_admin_user_two_groups(public_group, public_group2):
    return UserFactory(
        groups=[public_group, public_group2],
        roles=[models.Role.query.get("Group admin")],
    )


@pytest.fixture()
def super_admin_user(public_group, public_stream):
    return UserFactory(
        groups=[public_group],
        roles=[models.Role.query.get("Super admin")],
        streams=[public_stream],
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
def view_only_token2(user2):
    token_id = create_token(ACLs=[], user_id=user2.id, name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def view_only_token_group2(user_group2):
    token_id = create_token(ACLs=[], user_id=user_group2.id, name=str(uuid.uuid4()))
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
def annotation_token(user):
    token_id = create_token(ACLs=["Annotate"], user_id=user.id, name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def classification_token(user):
    token_id = create_token(ACLs=["Classify"], user_id=user.id, name=str(uuid.uuid4()))
    return token_id


@pytest.fixture()
def classification_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Classify"], user_id=user_two_groups.id, name=str(uuid.uuid4())
    )
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
def annotation_token_two_groups(user_two_groups):
    token_id = create_token(
        ACLs=["Annotate"], user_id=user_two_groups.id, name=str(uuid.uuid4())
    )
    return token_id


@pytest.fixture()
def public_group_sedm_allocation(sedm, public_group):
    return AllocationFactory(
        instrument=sedm,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )


@pytest.fixture()
def public_group2_sedm_allocation(sedm, public_group2):
    return AllocationFactory(
        instrument=sedm,
        group=public_group2,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )


@pytest.fixture()
def public_source_followup_request(public_group_sedm_allocation, public_source, user):
    return FollowupRequestFactory(
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


@pytest.fixture()
def public_source_group2_followup_request(
    public_group2_sedm_allocation, public_source_group2, user_two_groups
):
    return FollowupRequestFactory(
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


@pytest.fixture()
def sedm_listener_token(sedm, group_admin_user):
    token_id = create_token(
        ACLs=[sedm.listener_class.get_acl_id()],
        user_id=group_admin_user.id,
        name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def source_notification_user(public_group):
    uid = str(uuid.uuid4())
    username = f"{uid}@cesium.ml.org"
    user = User(
        username=username,
        contact_email=username,
        contact_phone="+12345678910",
        groups=[public_group],
        roles=[models.Role.query.get("Full user")],
        preferences={"allowEmailNotifications": True, "allowSMSNotifications": True},
    )
    DBSession().add(user)
    DBSession().commit()
    return user


@pytest.fixture()
def source_notification_user_token(source_notification_user):
    token_id = create_token(
        ACLs=[], user_id=source_notification_user.id, name=str(uuid.uuid4()),
    )
    return token_id


@pytest.fixture()
def public_taxonomy(public_group):
    return TaxonomyFactory(groups=[public_group])


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
    return CommentFactory(
        obj=public_source, groups=[public_group], author=user_no_groups
    )


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
    return AnnotationFactory(
        obj=public_source, groups=[public_group], author=user_no_groups
    )


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
    return ClassificationFactory(
        obj=public_source,
        groups=[public_group],
        author=user_two_groups,
        taxonomy=public_taxonomy,
    )


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
