"""Test fixture configuration."""

import base64
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import astroplan
import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa

from skyportal import models
from skyportal.model_util import create_token, delete_token
from skyportal.models import (
    Allocation,
    AllocationUser,
    AnalysisService,
    AnnotationOnPhotometry,
    AnnotationOnSpectrum,
    Candidate,
    CatalogQuery,
    ClassificationVote,
    CommentOnEarthquake,
    CommentOnGCN,
    CommentOnShift,
    CommentOnSpectrum,
    DBSession,
    DefaultAnalysis,
    DefaultFollowupRequest,
    DefaultGcnTag,
    DefaultObservationPlanRequest,
    DefaultSurveyEfficiencyRequest,
    EarthquakeEvent,
    EarthquakeMeasured,
    EarthquakeNotice,
    EarthquakePrediction,
    EventObservationPlan,
    EventObservationPlanStatistics,
    FacilityTransaction,
    FacilityTransactionRequest,
    FollowupRequest,
    FollowupRequestTargetGroup,
    FollowupRequestUser,
    Galaxy,
    GalaxyCatalog,
    GcnEvent,
    GcnEventUser,
    GcnNotice,
    GcnProperty,
    GcnReport,
    GcnSummary,
    GcnTag,
    GcnTrigger,
    GroupAdmissionRequest,
    GroupAnalysisService,
    GroupAnnotation,
    GroupAnnotationOnSpectrum,
    GroupClassification,
    GroupComment,
    GroupCommentOnEarthquake,
    GroupCommentOnGCN,
    GroupCommentOnShift,
    GroupCommentOnSpectrum,
    GroupDefaultAnalysis,
    GroupMMADetectorSpectrum,
    GroupMMADetectorTimeInterval,
    GroupObjAnalysis,
    GroupObjTag,
    GroupPhotometricSeries,
    GroupPhotometry,
    GroupPublicRelease,
    GroupReminder,
    GroupReminderOnEarthquake,
    GroupReminderOnGCN,
    GroupReminderOnShift,
    GroupReminderOnSpectrum,
    GroupScanReport,
    GroupSpectrum,
    GroupStream,
    GroupTaxonomy,
    GroupUser,
    Instrument,
    InstrumentField,
    InstrumentLog,
    Invitation,
    Listing,
    Localization,
    MMADetector,
    MMADetectorSpectrum,
    MMADetectorTimeInterval,
    Obj,
    ObjAnalysis,
    ObjTag,
    ObjTagOption,
    ObservationPlanRequest,
    ObservationPlanRequestTargetGroup,
    PhotometricSeries,
    Photometry,
    PhotometryValidation,
    PhotStat,
    PublicRelease,
    PublicSourcePage,
    RecurringAPI,
    Reminder,
    ReminderOnEarthquake,
    ReminderOnGCN,
    ReminderOnShift,
    ReminderOnSpectrum,
    Role,
    ScanReport,
    ScanReportItem,
    SharingService,
    SharingServiceCoauthor,
    SharingServiceGroup,
    SharingServiceGroupAutoPublisher,
    SharingServiceSubmission,
    Shift,
    ShiftUser,
    Source,
    SourceLabel,
    SourcesConfirmedInGCN,
    SourceView,
    SpatialCatalog,
    Spectrum,
    SpectrumObserver,
    SpectrumPI,
    SpectrumReducer,
    StreamInvitation,
    StreamPhotometricSeries,
    StreamPhotometry,
    StreamSharingService,
    StreamUser,
    SuperObj,
    SurveyEfficiencyForObservationPlan,
    SurveyEfficiencyForObservations,
    Telescope,
    Thumbnail,
    User,
    UserInvitation,
    Weather,
)
from skyportal.models.mmadetector import GcnEventMMADetector
from skyportal.tests.fixtures import (
    TMP_DIR,  # noqa: F401
    AllocationFactory,
    AnnotationFactory,
    ClassicalAssignmentFactory,
    ClassificationFactory,
    CommentFactory,
    FilterFactory,
    FollowupRequestFactory,
    GcnEventFactory,
    GroupFactory,
    InstrumentFactory,
    InvitationFactory,
    LocalizationFactory,
    NotificationFactory,
    ObjFactory,
    ObservingRunFactory,
    SpectrumFactory,
    StreamFactory,
    TaxonomyFactory,
    TelescopeFactory,
    ThumbnailFactory,
    UserFactory,
    UserNotificationFactory,
)
from skyportal.tests.test_util import page  # noqa: F401

from ..utils.naive_datetime import utcnow_naive

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

# Also add the frontend test user (testuser-cesium-ml-org) if needed so that the
# Playwright ``page`` fixture has a user to login as (without needing an
# invitation token). With invitations enabled on the test configs, login fails
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
    user is subsequently deleted, then the page will have no current_user.
    So, default back to the testuser-cesium-ml-org user upon frontend test
    completion.
    """
    yield  # Yield immediately since we only need to run teardown code
    if "page" in request.node.funcargs:
        testuser = (
            DBSession()
            .execute(sa.select(User).filter(User.username == "testuser-cesium-ml-org"))
            .scalars()
            .first()
        )
        request.node.funcargs["page"].goto(f"/become_user/{testuser.id}")


# check if a test has failed
@pytest.fixture(scope="function", autouse=True)
def test_failed_check(request):
    yield
    # request.node is an "item" because we use the default
    # "function" scope
    if request.node.rep_call.failed and "page" in request.node.funcargs:
        take_playwright_screenshot_and_page_source(
            request.node.funcargs["page"], request.node.nodeid
        )


# On failure, save a screenshot + page HTML for debugging.
def take_playwright_screenshot_and_page_source(page, nodeid):
    base = f"{nodeid}_{datetime.today().strftime('%Y-%m-%d_%H:%M')}".replace(
        "/", "_"
    ).replace(":", "_")
    base = os.path.join(os.path.dirname(__file__), "../../test-results", base)
    Path(base).parent.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=f"{base}.png", full_page=True)
        with open(f"{base}.html", "w") as f:
            f.write(page.content())
    except Exception as e:
        print(f"Could not capture Playwright failure artifacts: {e}")


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
def public_team(public_group):
    from skyportal.models import Team

    team = Team(name=str(uuid.uuid4()), groups=[public_group])
    DBSession().add(team)
    DBSession().commit()
    team_id = team.id
    yield team
    try:
        obj = DBSession().get(Team, team_id)
        if obj is not None:
            DBSession().delete(obj)
            DBSession().commit()
    except Exception:
        DBSession().rollback()


@pytest.fixture()
def public_group_team(public_team, public_group):
    from skyportal.models import GroupTeam

    return (
        DBSession()
        .execute(
            sa.select(GroupTeam).filter(
                GroupTeam.team_id == public_team.id,
                GroupTeam.group_id == public_group.id,
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
def public_super_obj(public_source):
    super_obj = SuperObj(name=str(uuid.uuid4()))
    super_obj.objs.append(public_source)
    DBSession.add(super_obj)
    DBSession.commit()
    super_obj_id = super_obj.id
    yield super_obj
    obj = (
        DBSession()
        .execute(sa.select(SuperObj).filter(SuperObj.id == super_obj_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_release(public_group):
    release = PublicRelease(
        name=str(uuid.uuid4()),
        link_name=str(uuid.uuid4()),
        description="test release",
        options={},
        groups=[public_group],
    )
    DBSession.add(release)
    DBSession.commit()
    release_id = release.id
    yield release
    obj = (
        DBSession()
        .execute(sa.select(PublicRelease).filter(PublicRelease.id == release_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_obj_tag(public_source, public_group, user):
    option = ObjTagOption(name=str(uuid.uuid4()))
    DBSession.add(option)
    DBSession.commit()
    option_id = option.id
    tag = ObjTag(
        objtagoption_id=option_id,
        obj_id=public_source.id,
        author_id=user.id,
    )
    tag.groups = [public_group]
    DBSession.add(tag)
    DBSession.commit()
    tag_id = tag.id
    yield tag
    for model, ident in ((ObjTag, tag_id), (ObjTagOption, option_id)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_source_page(public_source):
    page = PublicSourcePage(
        source_id=public_source.id,
        data={},
        hash=str(uuid.uuid4()),
    )
    DBSession.add(page)
    DBSession.commit()
    page_id = page.id
    yield page
    obj = (
        DBSession()
        .execute(sa.select(PublicSourcePage).filter(PublicSourcePage.id == page_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


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
        passed_at=utcnow_naive() - timedelta(seconds=np.random.randint(0, 100)),
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
            passed_at=utcnow_naive() - timedelta(seconds=np.random.randint(0, 100)),
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
            passed_at=utcnow_naive() - timedelta(seconds=np.random.randint(0, 100)),
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
def manage_teams_token(group_admin_user):
    token_id = create_token(
        ACLs=["Manage teams", "Upload data"],
        user_id=group_admin_user.id,
        name=str(uuid.uuid4()),
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
def gemini_north_instrument(p60_telescope):
    instrument = InstrumentFactory(
        name=f"Gemini North_{uuid.uuid4()}",
        type="imaging spectrograph",
        telescope=p60_telescope,
        band="Optical",
        filters=["sdssg", "sdssr", "sdssi"],
        api_classname="GEMINIAPI",
    )
    yield instrument
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_group_gemini_allocation(gemini_north_instrument, public_group):
    allocation = AllocationFactory(
        instrument=gemini_north_instrument,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
        altdata=json.dumps(
            {
                "user_email": "dummy@example.com",
                "user_key": "dummy-key",
                "programid": "GN-2026A-Q-102",
                "template_ids": [21],
            }
        ),
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
def winter_instrument(p60_telescope):
    instrument = InstrumentFactory(
        name=f"WINTER_{uuid.uuid4()}",
        type="imager",
        telescope=p60_telescope,
        band="NIR",
        filters=["sdssg", "sdssr", "sdssi"],
        api_classname="WINTERAPI",
    )
    yield instrument
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_group_winter_allocation(winter_instrument, public_group):
    allocation = AllocationFactory(
        instrument=winter_instrument,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
        altdata=json.dumps(
            {
                "program_name": "dummy-program",
                "program_api_key": "dummy-key",
                "username": "dummy-user",
                "password": "dummy-pass",
            }
        ),
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


# ---------------------------------------------------------------------------
# Auto-generated permission-coverage fixtures (ground-truth probed subset).
# ---------------------------------------------------------------------------


@pytest.fixture()
def public_analysis_service(public_group):
    analysis_service = AnalysisService(
        name=str(uuid.uuid4()),
        display_name=str(uuid.uuid4()),
        url="http://localhost:5000/analysis/test_service",
        authentication_type="none",
        enabled=True,
        analysis_type="lightcurve_fitting",
        input_data_types=["photometry"],
        optional_analysis_parameters={},
        groups=[public_group],
    )
    DBSession.add(analysis_service)
    DBSession.commit()
    analysis_service_id = analysis_service.id
    yield analysis_service
    obj = (
        DBSession()
        .execute(
            sa.select(AnalysisService).filter(AnalysisService.id == analysis_service_id)
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_annotation_on_photometry(public_source, public_group, user):
    annotation = AnnotationOnPhotometry(
        data={"unit_test": str(uuid.uuid4())},
        origin=str(uuid.uuid4()),
        obj_id=public_source.id,
        photometry_id=public_source.photometry[0].id,
        author_id=user.id,
        groups=[public_group],
    )
    DBSession.add(annotation)
    DBSession.commit()
    annotation_id = annotation.id
    yield annotation
    row = (
        DBSession()
        .execute(
            sa.select(AnnotationOnPhotometry).filter(
                AnnotationOnPhotometry.id == annotation_id
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_annotation_on_spectrum(public_source, public_group, user):
    spectrum = public_source.spectra[0]
    annotation = AnnotationOnSpectrum(
        data={"unit": "mag", "value": 1.0},
        origin=str(uuid.uuid4()),
        obj_id=public_source.id,
        spectrum_id=spectrum.id,
        author_id=user.id,
        groups=[public_group],
    )
    DBSession().add(annotation)
    DBSession().commit()
    annotation_id = annotation.id
    yield annotation
    obj = (
        DBSession()
        .execute(
            sa.select(AnnotationOnSpectrum).filter(
                AnnotationOnSpectrum.id == annotation_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_catalog_query(public_group, user):
    # Build an Instrument (+ Telescope) inline via the factory; associate the
    # Allocation with public_group so row-level access is meaningful.
    instrument = InstrumentFactory()
    instrument_id = instrument.id
    telescope_id = instrument.telescope.id

    allocation = Allocation(
        instrument_id=instrument_id,
        group_id=public_group.id,
        pi=uuid.uuid4().hex,
        proposal_id=uuid.uuid4().hex,
        hours_allocated=100,
    )
    DBSession.add(allocation)
    DBSession.commit()
    allocation_id = allocation.id

    catalog_query = CatalogQuery(
        allocation_id=allocation_id,
        requester_id=user.id,
        payload={},
        status="pending submission",
    )
    DBSession.add(catalog_query)
    DBSession.commit()
    catalog_query_id = catalog_query.id

    yield catalog_query

    for model, ident in (
        (CatalogQuery, catalog_query_id),
        (Allocation, allocation_id),
        (Instrument, instrument_id),
        (Telescope, telescope_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_classificationvote(public_group, public_source, user):
    taxonomy = TaxonomyFactory(groups=[public_group])
    taxonomy_id = taxonomy.id
    classification = ClassificationFactory(
        obj=public_source,
        groups=[public_group],
        author=user,
        taxonomy=taxonomy,
    )
    classification_id = classification.id
    vote = ClassificationVote(
        classification_id=classification_id,
        voter_id=user.id,
        vote=1,
    )
    DBSession.add(vote)
    DBSession.commit()
    vote_id = vote.id
    yield vote
    vote_obj = (
        DBSession()
        .execute(sa.select(ClassificationVote).filter(ClassificationVote.id == vote_id))
        .scalars()
        .first()
    )
    if vote_obj is not None:
        DBSession().delete(vote_obj)
        DBSession().commit()
    ClassificationFactory.teardown(classification)
    TaxonomyFactory.teardown(taxonomy_id)


@pytest.fixture()
def public_comment_on_earthquake(public_group, user):
    event = EarthquakeEvent(
        event_id=str(uuid.uuid4()),
        status="initial",
        sent_by_id=user.id,
    )
    DBSession.add(event)
    DBSession.commit()
    event_id = event.id

    comment = CommentOnEarthquake(
        text=str(uuid.uuid4()),
        earthquake_id=event_id,
        author_id=user.id,
        bot=False,
    )
    comment.groups = [public_group]
    DBSession.add(comment)
    DBSession.commit()
    comment_id = comment.id
    yield comment
    for model, ident in (
        (CommentOnEarthquake, comment_id),
        (EarthquakeEvent, event_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_comment_on_gcn_perm(public_group, user):
    gcn_event = GcnEvent(
        dateobs=utcnow_naive(),
        sent_by_id=user.id,
    )
    DBSession.add(gcn_event)
    DBSession.commit()
    gcn_event_id = gcn_event.id

    comment = CommentOnGCN(
        text=str(uuid.uuid4()),
        gcn_id=gcn_event_id,
        author_id=user.id,
        bot=False,
        groups=[public_group],
    )
    DBSession.add(comment)
    DBSession.commit()
    comment_id = comment.id
    yield comment
    comment = (
        DBSession()
        .execute(sa.select(CommentOnGCN).filter(CommentOnGCN.id == comment_id))
        .scalars()
        .first()
    )
    if comment is not None:
        DBSession().delete(comment)
        DBSession().commit()
    gcn_event = (
        DBSession()
        .execute(sa.select(GcnEvent).filter(GcnEvent.id == gcn_event_id))
        .scalars()
        .first()
    )
    if gcn_event is not None:
        DBSession().delete(gcn_event)
        DBSession().commit()


@pytest.fixture()
def public_comment_on_spectrum(public_source, public_group, user):
    instrument = InstrumentFactory()
    spectrum = Spectrum(
        wavelengths=np.array([5000.0, 5100.0, 5200.0]),
        fluxes=np.array([1.0, 2.0, 3.0]),
        obj_id=public_source.id,
        observed_at=utcnow_naive(),
        type="source",
        instrument_id=instrument.id,
        owner_id=user.id,
        groups=[public_group],
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id

    comment = CommentOnSpectrum(
        text=str(uuid.uuid4()),
        obj_id=public_source.id,
        spectrum_id=spectrum_id,
        author_id=user.id,
        bot=False,
        groups=[public_group],
    )
    DBSession.add(comment)
    DBSession.commit()
    comment_id = comment.id

    yield comment

    for model, ident in (
        (CommentOnSpectrum, comment_id),
        (Spectrum, spectrum_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_default_analysis(public_group, user):
    analysis_service = AnalysisService(
        name=str(uuid.uuid4()),
        display_name=str(uuid.uuid4()),
        url="http://localhost:5000/analysis/test_service",
        authentication_type="none",
        analysis_type="lightcurve_fitting",
        groups=[public_group],
    )
    DBSession.add(analysis_service)
    DBSession.commit()
    analysis_service_id = analysis_service.id

    default_analysis = DefaultAnalysis(
        analysis_service_id=analysis_service_id,
        author_id=user.id,
        source_filter={"classifications": [{"name": "Kilonova", "probability": 0.9}]},
        stats={},
        show_parameters=False,
        show_plots=False,
        show_corner=False,
        default_analysis_parameters={},
        groups=[public_group],
    )
    DBSession.add(default_analysis)
    DBSession.commit()
    default_analysis_id = default_analysis.id
    yield default_analysis
    for model, ident in (
        (DefaultAnalysis, default_analysis_id),
        (AnalysisService, analysis_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_default_followup_request(public_group, user):
    # Build a telescope -> instrument -> allocation chain inline, scoped to
    # public_group so that Allocation (and therefore DefaultFollowupRequest)
    # read access is meaningful for group members.
    telescope = Telescope(
        name=f"P48_{uuid.uuid4().hex}",
        nickname=f"P48_{uuid.uuid4().hex}",
        lat=33.3563,
        lon=-116.8650,
        elevation=1712.0,
        diameter=1.2,
        robotic=True,
    )
    DBSession.add(telescope)
    DBSession.commit()
    telescope_id = telescope.id

    instrument = Instrument(
        name=f"ZTF_{uuid.uuid4().hex}",
        type="imager",
        band="Optical",
        telescope=telescope,
        filters=["ztfg", "ztfr", "ztfi"],
    )
    DBSession.add(instrument)
    DBSession.commit()
    instrument_id = instrument.id

    allocation = Allocation(
        instrument=instrument,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )
    DBSession.add(allocation)
    DBSession.commit()
    allocation_id = allocation.id

    default_followup_request = DefaultFollowupRequest(
        requester=user,
        allocation=allocation,
        payload={
            "priority": "5",
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
        },
        default_followup_name=str(uuid.uuid4()),
        source_filter={},
    )
    DBSession.add(default_followup_request)
    DBSession.commit()
    default_followup_request_id = default_followup_request.id

    yield default_followup_request

    obj = (
        DBSession()
        .execute(
            sa.select(DefaultFollowupRequest).filter(
                DefaultFollowupRequest.id == default_followup_request_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()

    allocation = (
        DBSession()
        .execute(sa.select(Allocation).filter(Allocation.id == allocation_id))
        .scalars()
        .first()
    )
    if allocation is not None:
        DBSession().delete(allocation)
        DBSession().commit()

    instrument = (
        DBSession()
        .execute(sa.select(Instrument).filter(Instrument.id == instrument_id))
        .scalars()
        .first()
    )
    if instrument is not None:
        DBSession().delete(instrument)
        DBSession().commit()

    telescope = (
        DBSession()
        .execute(sa.select(Telescope).filter(Telescope.id == telescope_id))
        .scalars()
        .first()
    )
    if telescope is not None:
        DBSession().delete(telescope)
        DBSession().commit()


@pytest.fixture()
def public_default_gcn_tag(user):
    default_gcn_tag = DefaultGcnTag(
        requester_id=user.id,
        default_tag_name=str(uuid.uuid4()),
        filters={},
    )
    DBSession.add(default_gcn_tag)
    DBSession.commit()
    default_gcn_tag_id = default_gcn_tag.id
    yield default_gcn_tag
    row = (
        DBSession()
        .execute(
            sa.select(DefaultGcnTag).filter(DefaultGcnTag.id == default_gcn_tag_id)
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_default_observation_plan_request(public_group, user):
    allocation = AllocationFactory(
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )
    default_request = DefaultObservationPlanRequest(
        requester_id=user.id,
        allocation_id=allocation.id,
        payload={
            "observation_type": "Tiling",
            "filters": "ztfg",
            "exposure_time": 30,
        },
        filters={},
        default_plan_name=str(uuid.uuid4()),
        auto_send=False,
        target_groups=[public_group],
    )
    DBSession.add(default_request)
    DBSession.commit()
    default_request_id = default_request.id
    yield default_request
    row = (
        DBSession()
        .execute(
            sa.select(DefaultObservationPlanRequest).filter(
                DefaultObservationPlanRequest.id == default_request_id
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()
    AllocationFactory.teardown(allocation)


@pytest.fixture()
def public_default_observation_plan_request_target_group(public_group, user):
    from skyportal.models.observation_plan import (
        DefaultObservationPlanRequestTargetGroup,
    )

    # Build an Instrument (creates its Telescope too) and an Allocation
    # scoped to public_group so that DefaultObservationPlanRequest.read
    # (== Allocation.read == accessible_by_group_members) is meaningful.
    instrument = InstrumentFactory()
    allocation = AllocationFactory(
        instrument=instrument,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )

    # The parent DefaultObservationPlanRequest. requester is set to `user`
    # so that the create/update/delete policy
    # (AccessibleIfUserMatches("defaultobservationplanrequest.requester"))
    # makes `user` an authorized actor.
    default_request = DefaultObservationPlanRequest(
        requester_id=user.id,
        allocation_id=allocation.id,
        payload={},
        default_plan_name=str(uuid.uuid4()),
    )
    DBSession.add(default_request)
    DBSession.commit()
    default_request_id = default_request.id

    # The join row coupling the DefaultObservationPlanRequest to public_group.
    target_group = DefaultObservationPlanRequestTargetGroup(
        defaultobservationplanrequest_id=default_request_id,
        group_id=public_group.id,
    )
    DBSession.add(target_group)
    DBSession.commit()
    target_group_id = target_group.id

    yield target_group

    # Teardown by id; no-op if already gone.
    row = (
        DBSession()
        .execute(
            sa.select(DefaultObservationPlanRequestTargetGroup).filter(
                DefaultObservationPlanRequestTargetGroup.id == target_group_id
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()

    parent = (
        DBSession()
        .execute(
            sa.select(DefaultObservationPlanRequest).filter(
                DefaultObservationPlanRequest.id == default_request_id
            )
        )
        .scalars()
        .first()
    )
    if parent is not None:
        DBSession().delete(parent)
        DBSession().commit()

    AllocationFactory.teardown(allocation)
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_earthquake_event(user):
    event = EarthquakeEvent(
        event_id=str(uuid.uuid4()),
        status="initial",
        sent_by_id=user.id,
    )
    DBSession.add(event)
    DBSession.commit()
    event_id = event.id
    yield event
    obj = (
        DBSession()
        .execute(sa.select(EarthquakeEvent).filter(EarthquakeEvent.id == event_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_earthquake_measured(user):
    event = EarthquakeEvent(
        event_id=str(uuid.uuid4()),
        status="initial",
        sent_by_id=user.id,
    )
    DBSession.add(event)
    DBSession.commit()
    event_pk = event.id

    detector = MMADetector(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:8],
        type="gravitational-wave",
        fixed_location=True,
    )
    DBSession.add(detector)
    DBSession.commit()
    detector_id = detector.id

    measured = EarthquakeMeasured(
        event_id=event_pk,
        detector_id=detector_id,
        rfamp=0.0,
        lockloss=0,
    )
    DBSession.add(measured)
    DBSession.commit()
    measured_id = measured.id

    yield measured

    for model, ident in (
        (EarthquakeMeasured, measured_id),
        (MMADetector, detector_id),
        (EarthquakeEvent, event_pk),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_earthquake_notice(user):
    event = EarthquakeEvent(
        event_id=str(uuid.uuid4()),
        status="initial",
        sent_by_id=user.id,
    )
    DBSession.add(event)
    DBSession.commit()
    event_pk = event.id

    notice = EarthquakeNotice(
        sent_by_id=user.id,
        event_id=event.event_id,
        lat=0.0,
        lon=0.0,
        depth=0.0,
        magnitude=5.0,
        date=utcnow_naive(),
    )
    DBSession.add(notice)
    DBSession.commit()
    notice_id = notice.id
    yield notice
    for model, ident in ((EarthquakeNotice, notice_id), (EarthquakeEvent, event_pk)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_earthquake_prediction(user):
    detector = MMADetector(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:8],
        type="gravitational-wave",
        fixed_location=True,
    )
    DBSession.add(detector)
    DBSession.commit()
    detector_id = detector.id

    earthquake_event = EarthquakeEvent(
        event_id=str(uuid.uuid4()),
        status="initial",
        sent_by_id=user.id,
    )
    DBSession.add(earthquake_event)
    DBSession.commit()
    earthquake_event_id = earthquake_event.id

    now = utcnow_naive()
    prediction = EarthquakePrediction(
        event_id=earthquake_event.id,
        detector_id=detector.id,
        d=100.0,
        p=now,
        s=now,
        r2p0=now,
        r3p5=now,
        r5p0=now,
        rfamp=0.0,
        lockloss=0.0,
    )
    DBSession.add(prediction)
    DBSession.commit()
    prediction_id = prediction.id

    yield prediction

    obj = (
        DBSession()
        .execute(
            sa.select(EarthquakePrediction).filter(
                EarthquakePrediction.id == prediction_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()

    event = (
        DBSession()
        .execute(
            sa.select(EarthquakeEvent).filter(EarthquakeEvent.id == earthquake_event_id)
        )
        .scalars()
        .first()
    )
    if event is not None:
        DBSession().delete(event)
        DBSession().commit()

    det = (
        DBSession()
        .execute(sa.select(MMADetector).filter(MMADetector.id == detector_id))
        .scalars()
        .first()
    )
    if det is not None:
        DBSession().delete(det)
        DBSession().commit()


@pytest.fixture()
def public_event_observation_plan_statistics(public_group, super_admin_user):
    # Build the full dependency chain inline:
    # Telescope -> Instrument -> Allocation -> GcnEvent -> Localization
    # -> ObservationPlanRequest -> EventObservationPlan -> Statistics
    telescope = Telescope(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4()),
        lat=33.3563,
        lon=-116.8650,
        elevation=1712.0,
        diameter=1.2,
        robotic=True,
    )
    DBSession.add(telescope)
    DBSession.commit()
    telescope_id = telescope.id

    instrument = Instrument(
        name=str(uuid.uuid4()),
        type="imager",
        band="Optical",
        telescope_id=telescope_id,
        filters=["ztfg"],
    )
    DBSession.add(instrument)
    DBSession.commit()
    instrument_id = instrument.id

    allocation = Allocation(
        instrument_id=instrument_id,
        group_id=public_group.id,
        hours_allocated=100.0,
        types=["triggered"],
    )
    DBSession.add(allocation)
    DBSession.commit()
    allocation_id = allocation.id

    dateobs = utcnow_naive().replace(microsecond=0)
    gcnevent = GcnEvent(
        dateobs=dateobs,
        sent_by_id=super_admin_user.id,
        trigger_id=str(uuid.uuid4())[:20],
    )
    DBSession.add(gcnevent)
    DBSession.commit()
    gcnevent_id = gcnevent.id

    localization = Localization(
        dateobs=dateobs,
        localization_name=str(uuid.uuid4()),
        sent_by_id=super_admin_user.id,
        uniq=[4 * (4**29) + i for i in range(4)],
        probdensity=[0.25, 0.25, 0.25, 0.25],
    )
    DBSession.add(localization)
    DBSession.commit()
    localization_id = localization.id

    request = ObservationPlanRequest(
        requester_id=super_admin_user.id,
        gcnevent_id=gcnevent_id,
        localization_id=localization_id,
        allocation_id=allocation_id,
        payload={},
        status="complete",
    )
    DBSession.add(request)
    DBSession.commit()
    request_id = request.id

    observation_plan = EventObservationPlan(
        observation_plan_request_id=request_id,
        instrument_id=instrument_id,
        dateobs=dateobs,
        plan_name=str(uuid.uuid4()),
        validity_window_start=dateobs,
        validity_window_end=dateobs + timedelta(days=1),
        status="complete",
    )
    DBSession.add(observation_plan)
    DBSession.commit()
    observation_plan_id = observation_plan.id

    statistics = EventObservationPlanStatistics(
        observation_plan_id=observation_plan_id,
        localization_id=localization_id,
        statistics={},
    )
    DBSession.add(statistics)
    DBSession.commit()
    statistics_id = statistics.id

    yield statistics

    # Teardown in reverse dependency order; each delete no-ops if already gone.
    for model, ident in (
        (EventObservationPlanStatistics, statistics_id),
        (EventObservationPlan, observation_plan_id),
        (ObservationPlanRequest, request_id),
        (Localization, localization_id),
        (GcnEvent, gcnevent_id),
        (Allocation, allocation_id),
        (Instrument, instrument_id),
        (Telescope, telescope_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_facility_transaction_request(user):
    request = FacilityTransactionRequest(
        method="GET",
        endpoint=str(uuid.uuid4()),
        data={},
        params={},
        headers={},
        status="pending submission",
        initiator_id=user.id,
    )
    DBSession.add(request)
    DBSession.commit()
    request_id = request.id
    yield request
    row = (
        DBSession()
        .execute(
            sa.select(FacilityTransactionRequest).filter(
                FacilityTransactionRequest.id == request_id
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_followup_request_user(public_group, public_source, user):
    # Build the parent FollowupRequest inline. A FollowupRequest needs an Obj
    # (public_source), an Allocation, a payload, a status and a requester.
    # The Allocation is scoped to public_group so that row-level read access
    # is meaningful (members of public_group can read it, outsiders cannot).
    telescope = TelescopeFactory(
        name=f"telescope_{uuid.uuid4()}",
        nickname=f"tel_{uuid.uuid4()}",
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        diameter=1.0,
    )
    instrument = InstrumentFactory(
        name=f"instrument_{uuid.uuid4()}",
        type="imaging spectrograph",
        telescope=telescope,
        band="Optical",
        filters=["sdssu", "sdssg", "sdssr", "sdssi"],
    )
    allocation = AllocationFactory(
        instrument=instrument,
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )

    followup_request = FollowupRequest(
        obj_id=public_source.id,
        allocation_id=allocation.id,
        payload={
            "priority": "5",
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
        },
        status="pending submission",
        requester_id=user.id,
        last_modified_by_id=user.id,
    )
    DBSession().add(followup_request)
    DBSession().commit()

    # The join row points at `user`, so update/delete (AccessibleIfUserMatches
    # on "user") are satisfied only by that user (and the system admin).
    followup_request_user = FollowupRequestUser(
        followuprequest_id=followup_request.id, user_id=user.id
    )
    DBSession().add(followup_request_user)
    DBSession().commit()

    followup_request_user_id = followup_request_user.id
    followup_request_id = followup_request.id
    allocation_id = allocation.id

    yield followup_request_user

    join_row = (
        DBSession()
        .execute(
            sa.select(FollowupRequestUser).filter(
                FollowupRequestUser.id == followup_request_user_id
            )
        )
        .scalars()
        .first()
    )
    if join_row is not None:
        DBSession().delete(join_row)
        DBSession().commit()

    request_row = (
        DBSession()
        .execute(
            sa.select(FollowupRequest).filter(FollowupRequest.id == followup_request_id)
        )
        .scalars()
        .first()
    )
    if request_row is not None:
        DBSession().delete(request_row)
        DBSession().commit()

    allocation_row = (
        DBSession()
        .execute(sa.select(Allocation).filter(Allocation.id == allocation_id))
        .scalars()
        .first()
    )
    if allocation_row is not None:
        AllocationFactory.teardown(allocation_row)


@pytest.fixture()
def public_galaxy_catalog():
    catalog = GalaxyCatalog(
        name=str(uuid.uuid4()),
        description="test galaxy catalog",
        url="http://example.com/catalog",
    )
    DBSession.add(catalog)
    DBSession.commit()
    catalog_id = catalog.id
    yield catalog
    obj = (
        DBSession()
        .execute(sa.select(GalaxyCatalog).filter(GalaxyCatalog.id == catalog_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_gcnevent(user):
    gcnevent = GcnEvent(
        dateobs=utcnow_naive(),
        sent_by_id=user.id,
        trigger_id=str(uuid.uuid4().int)[:10],
    )
    DBSession.add(gcnevent)
    DBSession.commit()
    gcnevent_id = gcnevent.id
    yield gcnevent
    obj = (
        DBSession()
        .execute(sa.select(GcnEvent).filter(GcnEvent.id == gcnevent_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_gcn_event_mmadetector(user):
    # GcnEvent.dateobs is unique; use a deterministic-but-unique value
    dateobs = utcnow_naive().replace(microsecond=int(uuid.uuid4().int % 1000000))
    event = GcnEvent(
        dateobs=dateobs,
        sent_by_id=user.id,
        trigger_id=str(uuid.uuid4().int % 1000000000),
    )
    DBSession.add(event)
    DBSession.commit()
    event_dateobs = event.dateobs

    detector = MMADetector(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:8],
        type="gravitational-wave",
        fixed_location=True,
    )
    DBSession.add(detector)
    DBSession.commit()
    detector_id = detector.id

    join = GcnEventMMADetector(
        gcnevent_id=event.id,
        mmadetector_id=detector.id,
    )
    DBSession.add(join)
    DBSession.commit()
    join_id = join.id

    yield join

    # Teardown: delete join row, then detector, then event; no-op if already gone
    join_obj = (
        DBSession()
        .execute(
            sa.select(GcnEventMMADetector).filter(GcnEventMMADetector.id == join_id)
        )
        .scalars()
        .first()
    )
    if join_obj is not None:
        DBSession().delete(join_obj)
        DBSession().commit()

    detector_obj = (
        DBSession()
        .execute(sa.select(MMADetector).filter(MMADetector.id == detector_id))
        .scalars()
        .first()
    )
    if detector_obj is not None:
        DBSession().delete(detector_obj)
        DBSession().commit()

    event_obj = (
        DBSession()
        .execute(sa.select(GcnEvent).filter(GcnEvent.dateobs == event_dateobs))
        .scalars()
        .first()
    )
    if event_obj is not None:
        DBSession().delete(event_obj)
        DBSession().commit()


@pytest.fixture()
def public_gcnevent_user(user):
    gcnevent = GcnEvent(
        dateobs=str(uuid.uuid4()),
        sent_by_id=user.id,
    )
    # dateobs must be a real datetime; use a unique time to satisfy the unique
    # constraint without colliding with other tests
    gcnevent.dateobs = utcnow_naive() + timedelta(seconds=np.random.randint(0, 10**8))
    DBSession.add(gcnevent)
    DBSession.commit()
    gcnevent_id = gcnevent.id

    gcnevent_user = GcnEventUser(
        gcnevent_id=gcnevent_id,
        user_id=user.id,
    )
    DBSession.add(gcnevent_user)
    DBSession.commit()
    gcnevent_user_id = gcnevent_user.id

    yield gcnevent_user

    for model, ident in (
        (GcnEventUser, gcnevent_user_id),
        (GcnEvent, gcnevent_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_gcn_property(public_group, user):
    dateobs = utcnow_naive().replace(microsecond=0) + timedelta(
        seconds=int(uuid.uuid4().int % 1000000)
    )
    gcnevent = GcnEvent(
        dateobs=dateobs,
        sent_by_id=user.id,
    )
    DBSession.add(gcnevent)
    DBSession.commit()

    gcn_property = GcnProperty(
        dateobs=dateobs,
        sent_by_id=user.id,
        data={"test_property": 1.0},
    )
    DBSession.add(gcn_property)
    DBSession.commit()
    gcn_property_id = gcn_property.id
    yield gcn_property
    for model, ident, col in (
        (GcnProperty, gcn_property_id, GcnProperty.id),
        (GcnEvent, dateobs, GcnEvent.dateobs),
    ):
        row = (
            DBSession().execute(sa.select(model).filter(col == ident)).scalars().first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_gcn_report(public_group, user):
    # Create a parent GcnEvent inline (only sent_by_id and dateobs are required).
    dateobs = utcnow_naive().replace(microsecond=0)
    gcnevent = GcnEvent(
        dateobs=dateobs,
        sent_by_id=user.id,
    )
    DBSession.add(gcnevent)
    DBSession.commit()

    report = GcnReport(
        sent_by_id=user.id,
        dateobs=dateobs,
        group_id=public_group.id,
        data={},
        report_name=str(uuid.uuid4()),
        published=False,
    )
    DBSession.add(report)
    DBSession.commit()
    report_id = report.id
    yield report
    for model, ident, attr in (
        (GcnReport, report_id, "id"),
        (GcnEvent, dateobs, "dateobs"),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(getattr(model, attr) == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_gcn_summary(public_group, user):
    dateobs = datetime.now(UTC).replace(tzinfo=None)

    gcnevent = GcnEvent(
        dateobs=dateobs,
        sent_by_id=user.id,
    )
    DBSession.add(gcnevent)
    DBSession.commit()
    event_dateobs = gcnevent.dateobs

    summary = GcnSummary(
        sent_by_id=user.id,
        dateobs=event_dateobs,
        group_id=public_group.id,
        title=str(uuid.uuid4()),
        text=str(uuid.uuid4()),
    )
    DBSession.add(summary)
    DBSession.commit()
    summary_id = summary.id
    yield summary
    for model, ident in ((GcnSummary, summary_id), (GcnEvent, event_dateobs)):
        if model is GcnSummary:
            row = (
                DBSession()
                .execute(sa.select(model).filter(model.id == ident))
                .scalars()
                .first()
            )
        else:
            row = (
                DBSession()
                .execute(sa.select(model).filter(model.dateobs == ident))
                .scalars()
                .first()
            )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_gcn_tag(public_group, user):
    # GcnTag is keyed to a GcnEvent via the dateobs foreign key, so we
    # create a parent GcnEvent inline (unique dateobs to avoid the unique
    # constraint) and tear it down alongside the tag.
    dateobs = utcnow_naive().replace(microsecond=0) + timedelta(
        seconds=int(uuid.uuid4().int % 1000000)
    )
    gcnevent = GcnEvent(
        dateobs=dateobs,
        sent_by_id=user.id,
    )
    DBSession.add(gcnevent)
    DBSession.commit()
    gcnevent_id = gcnevent.id

    tag = GcnTag(
        dateobs=dateobs,
        text=str(uuid.uuid4()),
        sent_by_id=user.id,
    )
    DBSession.add(tag)
    DBSession.commit()
    tag_id = tag.id

    yield tag

    for model, ident in ((GcnTag, tag_id), (GcnEvent, gcnevent_id)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_admission_request(public_group, user):
    request = GroupAdmissionRequest(
        user_id=user.id,
        group_id=public_group.id,
        status="pending",
    )
    DBSession.add(request)
    DBSession.commit()
    request_id = request.id
    yield request
    obj = (
        DBSession()
        .execute(
            sa.select(GroupAdmissionRequest).filter(
                GroupAdmissionRequest.id == request_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_group_analysis_service(public_group):
    analysis_service = AnalysisService(
        name=str(uuid.uuid4()),
        display_name=str(uuid.uuid4()),
        url="http://localhost:5000/analysis/" + str(uuid.uuid4()),
        authentication_type="none",
        analysis_type="lightcurve_fitting",
    )
    DBSession.add(analysis_service)
    DBSession.commit()
    analysis_service_id = analysis_service.id

    group_analysis_service = GroupAnalysisService(
        group_id=public_group.id,
        analysis_service_id=analysis_service_id,
    )
    DBSession.add(group_analysis_service)
    DBSession.commit()
    group_analysis_service_id = group_analysis_service.id

    yield group_analysis_service

    for model, ident in (
        (GroupAnalysisService, group_analysis_service_id),
        (AnalysisService, analysis_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_allocation_user(public_group, user):
    allocation = AllocationFactory(group=public_group)
    DBSession().commit()
    allocation_id = allocation.id
    instrument = allocation.instrument

    allocation_user = AllocationUser(
        allocation_id=allocation_id,
        user_id=user.id,
    )
    DBSession().add(allocation_user)
    DBSession().commit()
    allocation_user_id = allocation_user.id
    yield allocation_user

    au = (
        DBSession()
        .execute(
            sa.select(AllocationUser).filter(AllocationUser.id == allocation_user_id)
        )
        .scalars()
        .first()
    )
    if au is not None:
        DBSession().delete(au)
        DBSession().commit()

    alloc = (
        DBSession()
        .execute(sa.select(Allocation).filter(Allocation.id == allocation_id))
        .scalars()
        .first()
    )
    if alloc is not None:
        DBSession().delete(alloc)
        DBSession().commit()
        InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_comment_on_shift(public_group, user):
    shift = Shift(
        name=str(uuid.uuid4()),
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1),
        group_id=public_group.id,
    )
    DBSession.add(shift)
    DBSession.commit()
    shift_id = shift.id

    comment = CommentOnShift(
        text=str(uuid.uuid4()),
        shift_id=shift_id,
        author_id=user.id,
        bot=False,
    )
    comment.groups = [public_group]
    DBSession.add(comment)
    DBSession.commit()
    comment_id = comment.id
    yield comment
    for model, ident in ((CommentOnShift, comment_id), (Shift, shift_id)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_default_survey_efficiency_request(public_group):
    # Build the parent DefaultObservationPlanRequest chain inline.
    # Telescope -> Instrument -> Allocation (scoped to public_group) ->
    # DefaultObservationPlanRequest -> DefaultSurveyEfficiencyRequest.
    telescope = TelescopeFactory(
        name=f"Telescope_{uuid.uuid4()}",
        nickname=f"Scope_{uuid.uuid4()}",
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        diameter=1.0,
    )
    telescope_id = telescope.id

    instrument = InstrumentFactory(
        name=f"Instrument_{uuid.uuid4()}",
        type="imaging spectrograph",
        telescope=telescope,
        band="Optical",
        filters=["sdssu", "sdssg", "sdssr", "sdssi"],
        api_classname="GENERICAPI",
    )

    allocation = AllocationFactory(
        instrument=instrument,
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

    default_obs_plan = DefaultObservationPlanRequest(
        payload={},
        allocation_id=allocation.id,
        default_plan_name=str(uuid.uuid4()),
    )
    DBSession.add(default_obs_plan)
    DBSession.commit()
    default_obs_plan_id = default_obs_plan.id

    default_survey_efficiency = DefaultSurveyEfficiencyRequest(
        default_observationplan_request_id=default_obs_plan_id,
        payload={},
    )
    DBSession.add(default_survey_efficiency)
    DBSession.commit()
    default_survey_efficiency_id = default_survey_efficiency.id

    yield default_survey_efficiency

    for model, ident in (
        (DefaultSurveyEfficiencyRequest, default_survey_efficiency_id),
        (DefaultObservationPlanRequest, default_obs_plan_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()

    AllocationFactory.teardown(allocation)
    InstrumentFactory.teardown(instrument)
    TelescopeFactory.teardown(telescope_id)


@pytest.fixture()
def public_event_observation_plan(public_group, user):
    # Build the parent chain inline: Instrument (+Telescope) and Allocation via
    # factories, a GcnEvent with a Localization, then an ObservationPlanRequest,
    # and finally the EventObservationPlan itself.
    allocation = AllocationFactory(group=public_group)
    instrument = allocation.instrument

    dateobs = datetime.utcnow()
    gcnevent = GcnEventFactory(dateobs=dateobs, sent_by=user)

    localization = LocalizationFactory(
        dateobs=dateobs,
        sent_by=user,
        localization_name=str(uuid.uuid4().hex),
        notice_id=None,
    )
    DBSession().add(localization)
    DBSession().commit()

    request = ObservationPlanRequest(
        requester_id=user.id,
        gcnevent_id=gcnevent.id,
        localization_id=localization.id,
        allocation_id=allocation.id,
        payload={},
        status="pending submission",
    )
    DBSession().add(request)
    DBSession().commit()

    plan = EventObservationPlan(
        observation_plan_request_id=request.id,
        instrument_id=instrument.id,
        dateobs=dateobs,
        plan_name=str(uuid.uuid4()),
        validity_window_start=dateobs,
        validity_window_end=dateobs + timedelta(days=1),
        status="pending submission",
    )
    DBSession().add(plan)
    DBSession().commit()

    plan_id = plan.id
    request_id = request.id
    localization_id = localization.id

    yield plan

    plan_obj = (
        DBSession()
        .execute(
            sa.select(EventObservationPlan).filter(EventObservationPlan.id == plan_id)
        )
        .scalars()
        .first()
    )
    if plan_obj is not None:
        DBSession().delete(plan_obj)
        DBSession().commit()

    request_obj = (
        DBSession()
        .execute(
            sa.select(ObservationPlanRequest).filter(
                ObservationPlanRequest.id == request_id
            )
        )
        .scalars()
        .first()
    )
    if request_obj is not None:
        DBSession().delete(request_obj)
        DBSession().commit()

    localization_obj = (
        DBSession()
        .execute(sa.select(Localization).filter(Localization.id == localization_id))
        .scalars()
        .first()
    )
    if localization_obj is not None:
        LocalizationFactory.teardown(localization_obj)

    GcnEventFactory.teardown(gcnevent)
    AllocationFactory.teardown(allocation)


@pytest.fixture()
def public_facility_transaction(user):
    transaction = FacilityTransaction(
        created_at=datetime.utcnow(),
        request={"method": "POST", "endpoint": str(uuid.uuid4())},
        response={"status": 200, "content": str(uuid.uuid4())},
        initiator_id=user.id,
    )
    DBSession.add(transaction)
    DBSession.commit()
    transaction_id = transaction.id
    yield transaction
    obj = (
        DBSession()
        .execute(
            sa.select(FacilityTransaction).filter(
                FacilityTransaction.id == transaction_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_galaxy():
    catalog = GalaxyCatalog(name=str(uuid.uuid4()))
    DBSession.add(catalog)
    DBSession.commit()
    catalog_id = catalog.id
    galaxy = Galaxy(
        catalog_id=catalog_id,
        name=str(uuid.uuid4()),
        ra=30.0,
        dec=45.0,
        distmpc=100.0,
        redshift=0.02,
    )
    DBSession.add(galaxy)
    DBSession.commit()
    galaxy_id = galaxy.id
    yield galaxy
    for model, ident in ((Galaxy, galaxy_id), (GalaxyCatalog, catalog_id)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_gcn_notice(user):
    dateobs = datetime.utcnow().replace(microsecond=0)

    gcnevent = GcnEvent(
        dateobs=dateobs,
        trigger_id=str(uuid.uuid4().int)[:10],
        sent_by_id=user.id,
    )
    DBSession.add(gcnevent)
    DBSession.commit()

    notice = GcnNotice(
        sent_by_id=user.id,
        ivorn=str(uuid.uuid4()),
        notice_type="Test",
        notice_format="voevent",
        stream="Test",
        date=dateobs,
        dateobs=dateobs,
        content=bytes(1024),
        has_localization=False,
        localization_ingested=False,
    )
    DBSession.add(notice)
    DBSession.commit()
    notice_id = notice.id
    yield notice
    for model, ident in ((GcnNotice, notice_id), (GcnEvent, dateobs)):
        row = (
            DBSession()
            .execute(
                sa.select(model).filter(
                    (GcnNotice.id == ident)
                    if model is GcnNotice
                    else (GcnEvent.dateobs == ident)
                )
            )
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_gcn_trigger(public_group, user):
    # Build the parents inline. GcnTrigger is a join_model coupling a
    # GcnEvent (by dateobs) and an Allocation (by allocation_id), with an
    # extra nullable=False `triggered` boolean column.

    # Instrument (creates its own Telescope via SubFactory) needed by Allocation.
    instrument = InstrumentFactory()
    DBSession().commit()

    # Allocation scoped to public_group so its access is meaningful.
    allocation = AllocationFactory(
        instrument=instrument,
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
    DBSession().commit()
    allocation_id = allocation.id

    # GcnTrigger create/update/delete is gated on the actor being an
    # AllocationUser of the trigger's allocation. Link `user` so they are an
    # insider for those modes (group_admin_user / user_group2 remain outsiders).
    allocation_user = AllocationUser(allocation_id=allocation_id, user_id=user.id)
    DBSession().add(allocation_user)
    DBSession().commit()
    allocation_user_id = allocation_user.id

    # Minimal GcnEvent: only dateobs (unique, nullable=False) and sent_by are
    # required; no localization/parquet files needed.
    gcnevent = GcnEventFactory(sent_by=user)
    DBSession().commit()
    dateobs = gcnevent.dateobs

    gcn_trigger = GcnTrigger(
        dateobs=dateobs,
        allocation_id=allocation_id,
        triggered=True,
    )
    DBSession().add(gcn_trigger)
    DBSession().commit()
    gcn_trigger_id = gcn_trigger.id

    yield gcn_trigger

    for model, ident in (
        (GcnTrigger, gcn_trigger_id),
        (AllocationUser, allocation_user_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()

    GcnEventFactory.teardown(gcnevent)

    allocation = (
        DBSession()
        .execute(sa.select(Allocation).filter(Allocation.id == allocation_id))
        .scalars()
        .first()
    )
    if allocation is not None:
        AllocationFactory.teardown(allocation)
    else:
        InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_group_annotation_on_photometry(public_group, public_source, user):
    # Build an Instrument (+ Telescope) inline for the Photometry parent.
    instrument = InstrumentFactory()

    # Photometry parent, shared with public_group and owned by `user`
    # so that group members and the owner can read it.
    phot = Photometry(
        obj_id=public_source.id,
        mjd=58000.0,
        flux=12.34,
        fluxerr=0.5,
        filter="ztfg",
        origin=str(uuid.uuid4()),
        upload_id=str(uuid.uuid4()),
        instrument_id=instrument.id,
        owner_id=user.id,
    )
    phot.groups = [public_group]
    DBSession.add(phot)
    DBSession.commit()
    phot_id = phot.id

    # AnnotationOnPhotometry parent, authored by `user`, scoped to public_group.
    annotation = models.AnnotationOnPhotometry(
        obj_id=public_source.id,
        photometry_id=phot_id,
        author_id=user.id,
        origin=str(uuid.uuid4()),
        data={},
    )
    DBSession.add(annotation)
    DBSession.commit()
    annotation_id = annotation.id

    # The join row coupling the Group and the AnnotationOnPhotometry.
    join = models.GroupAnnotationOnPhotometry(
        group_id=public_group.id,
        annotations_on_photometr_id=annotation_id,
    )
    DBSession.add(join)
    DBSession.commit()
    join_id = join.id

    yield join

    for model, ident in (
        (models.GroupAnnotationOnPhotometry, join_id),
        (models.AnnotationOnPhotometry, annotation_id),
        (Photometry, phot_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()

    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_group_annotation_on_spectrum(public_group, public_source, user):
    # Instrument (plus its telescope) needed to build a Spectrum.
    instrument = InstrumentFactory()

    spectrum = Spectrum(
        obj_id=public_source.id,
        wavelengths=np.sort(1000 * np.random.random(20)),
        fluxes=1e-9 * np.random.random(20),
        observed_at=datetime.now(),
        instrument_id=instrument.id,
        owner_id=user.id,
        type="source",
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id

    annotation = AnnotationOnSpectrum(
        obj_id=public_source.id,
        spectrum_id=spectrum_id,
        author_id=user.id,
        origin=str(uuid.uuid4()),
        data={"value": 1.0},
    )
    DBSession.add(annotation)
    DBSession.commit()
    annotation_id = annotation.id

    join = GroupAnnotationOnSpectrum(
        group_id=public_group.id,
        annotations_on_spectr_id=annotation_id,
    )
    DBSession.add(join)
    DBSession.commit()
    join_id = join.id

    yield join

    for model, ident in (
        (GroupAnnotationOnSpectrum, join_id),
        (AnnotationOnSpectrum, annotation_id),
        (Spectrum, spectrum_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()

    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_group_comment_on_earthquake(public_group, user):
    earthquake = EarthquakeEvent(
        event_id=str(uuid.uuid4()),
        status="initial",
        sent_by_id=user.id,
    )
    DBSession.add(earthquake)
    DBSession.commit()
    earthquake_id = earthquake.id

    comment = CommentOnEarthquake(
        text=str(uuid.uuid4()),
        bot=False,
        earthquake_id=earthquake_id,
        author_id=user.id,
    )
    DBSession.add(comment)
    DBSession.commit()
    comment_id = comment.id

    group_comment = GroupCommentOnEarthquake(
        group_id=public_group.id,
        comments_on_earthquake_id=comment_id,
    )
    DBSession.add(group_comment)
    DBSession.commit()
    group_comment_id = group_comment.id

    yield group_comment

    for model, ident in (
        (GroupCommentOnEarthquake, group_comment_id),
        (CommentOnEarthquake, comment_id),
        (EarthquakeEvent, earthquake_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_comment_on_gcn(public_group, user):
    # Create a parent GcnEvent inline (GcnEvent read/create is public).
    gcn_event = GcnEvent(
        dateobs=utcnow_naive(),
        sent_by_id=user.id,
    )
    DBSession.add(gcn_event)
    DBSession.commit()
    gcn_event_id = gcn_event.id

    # Create the parent CommentOnGCN, scoped to public_group and authored by `user`.
    comment = CommentOnGCN(
        text=str(uuid.uuid4()),
        bot=False,
        author_id=user.id,
        gcn_id=gcn_event_id,
    )
    DBSession.add(comment)
    DBSession.commit()
    comment_id = comment.id

    # Create the join row linking the Group and the CommentOnGCN.
    group_comment = GroupCommentOnGCN(
        group_id=public_group.id,
        comments_on_gcn_id=comment_id,
    )
    DBSession.add(group_comment)
    DBSession.commit()
    group_comment_id = group_comment.id

    yield group_comment

    join_obj = (
        DBSession()
        .execute(
            sa.select(GroupCommentOnGCN).filter(
                GroupCommentOnGCN.id == group_comment_id
            )
        )
        .scalars()
        .first()
    )
    if join_obj is not None:
        DBSession().delete(join_obj)
        DBSession().commit()

    comment_obj = (
        DBSession()
        .execute(sa.select(CommentOnGCN).filter(CommentOnGCN.id == comment_id))
        .scalars()
        .first()
    )
    if comment_obj is not None:
        DBSession().delete(comment_obj)
        DBSession().commit()

    gcn_obj = (
        DBSession()
        .execute(sa.select(GcnEvent).filter(GcnEvent.id == gcn_event_id))
        .scalars()
        .first()
    )
    if gcn_obj is not None:
        DBSession().delete(gcn_obj)
        DBSession().commit()


@pytest.fixture()
def public_group_comment_on_shift(public_group, user):
    shift = Shift(
        name=str(uuid.uuid4()),
        group_id=public_group.id,
        start_date=utcnow_naive(),
        end_date=utcnow_naive() + timedelta(days=1),
    )
    DBSession.add(shift)
    DBSession.commit()
    shift_id = shift.id

    comment = CommentOnShift(
        text=str(uuid.uuid4()),
        shift_id=shift_id,
        author_id=user.id,
        bot=False,
    )
    DBSession.add(comment)
    DBSession.commit()
    comment_id = comment.id

    group_comment = GroupCommentOnShift(
        group_id=public_group.id,
        comments_on_shift_id=comment_id,
    )
    DBSession.add(group_comment)
    DBSession.commit()
    group_comment_id = group_comment.id

    yield group_comment

    for model, ident in (
        (GroupCommentOnShift, group_comment_id),
        (CommentOnShift, comment_id),
        (Shift, shift_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_comment_on_spectrum(public_group, public_source, user):
    # Parent 1: a Spectrum on the public_source's obj, visible to public_group.
    # SpectrumFactory creates (and tears down) its own Instrument/Telescope and
    # the reducer/observer users; we just attach the obj, group, and owner.
    spectrum = SpectrumFactory(
        obj=public_source,
        groups=[public_group],
    )
    DBSession().add(spectrum)
    DBSession().commit()

    # Parent 2: a CommentOnSpectrum authored by `user`, scoped to public_group.
    comment = CommentOnSpectrum(
        text=str(uuid.uuid4()),
        obj_id=public_source.id,
        spectrum_id=spectrum.id,
        author=user,
        bot=False,
    )
    DBSession().add(comment)
    DBSession().commit()

    # The join row coupling public_group <-> the CommentOnSpectrum.
    join = GroupCommentOnSpectrum(
        group_id=public_group.id,
        comments_on_spectr_id=comment.id,
    )
    DBSession().add(join)
    DBSession().commit()

    join_id = join.id
    comment_id = comment.id

    yield join

    # Teardown join row first (no-op if already gone).
    obj = (
        DBSession()
        .execute(
            sa.select(GroupCommentOnSpectrum).filter(
                GroupCommentOnSpectrum.id == join_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()

    # Tear down the CommentOnSpectrum parent (fires after_delete listener that
    # removes on-disk attachment data; safe here since there is no attachment).
    comment_obj = (
        DBSession()
        .execute(
            sa.select(CommentOnSpectrum).filter(CommentOnSpectrum.id == comment_id)
        )
        .scalars()
        .first()
    )
    if comment_obj is not None:
        DBSession().delete(comment_obj)
        DBSession().commit()

    # Tear down the Spectrum parent (also removes its Instrument and the
    # reducer/observer users created by SpectrumFactory).
    SpectrumFactory.teardown(spectrum)


@pytest.fixture()
def public_group_default_analysis(public_group, user):
    analysis_service = AnalysisService(
        name=str(uuid.uuid4()),
        display_name="test analysis service",
        url="http://localhost:5000/analysis/test_service",
        authentication_type="none",
        analysis_type="lightcurve_fitting",
        groups=[public_group],
    )
    DBSession.add(analysis_service)
    DBSession.commit()
    analysis_service_id = analysis_service.id

    default_analysis = DefaultAnalysis(
        analysis_service_id=analysis_service_id,
        show_parameters=False,
        show_plots=False,
        show_corner=False,
        source_filter={"classifications": {"name": "Kilonova", "probability": 0.9}},
        stats={},
        author_id=user.id,
    )
    DBSession.add(default_analysis)
    DBSession.commit()
    default_analysis_id = default_analysis.id

    group_default_analysis = GroupDefaultAnalysis(
        group_id=public_group.id,
        default_analyse_id=default_analysis_id,
    )
    DBSession.add(group_default_analysis)
    DBSession.commit()
    group_default_analysis_id = group_default_analysis.id

    yield group_default_analysis

    for model, ident in (
        (GroupDefaultAnalysis, group_default_analysis_id),
        (DefaultAnalysis, default_analysis_id),
        (AnalysisService, analysis_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_invitation(public_group, user):
    # GroupInvitation = join_model("group_invitations", Group, Invitation).
    # Build the parent Invitation first (invited_by=user so that
    # Invitation.read = AccessibleIfUserMatches("invited_by") resolves to `user`),
    # then explicitly link it to public_group via the GroupInvitation join row.
    # NOTE: Invitation fires an `after_insert` email listener; emailing is gated by
    # the `invitations.disable_emailing` config which the test suite sets, so no real
    # email is sent here.
    invitation = InvitationFactory(invited_by=user)
    group_invitation = models.GroupInvitation(
        group_id=public_group.id,
        invitation_id=invitation.id,
    )
    DBSession.add(group_invitation)
    DBSession.commit()
    group_invitation_id = group_invitation.id
    yield group_invitation
    obj = (
        DBSession()
        .execute(
            sa.select(models.GroupInvitation).filter(
                models.GroupInvitation.id == group_invitation_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()
    InvitationFactory.teardown(invitation)


@pytest.fixture()
def public_group_mmadetector_spectrum(public_group, user):
    from datetime import datetime as _dt

    detector = MMADetector(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:8],
        type="gravitational-wave",
    )
    DBSession.add(detector)
    DBSession.commit()
    detector_id = detector.id

    spectrum = MMADetectorSpectrum(
        frequencies=np.array([1.0, 2.0, 3.0]),
        amplitudes=np.array([1.0e-23, 2.0e-23, 3.0e-23]),
        start_time=_dt(2020, 1, 1, 0, 0, 0),
        end_time=_dt(2020, 1, 1, 1, 0, 0),
        detector_id=detector_id,
        owner_id=user.id,
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id

    join = GroupMMADetectorSpectrum(
        group_id=public_group.id,
        detector_spectr_id=spectrum_id,
    )
    DBSession.add(join)
    DBSession.commit()
    join_id = join.id

    yield join

    for model, ident in (
        (GroupMMADetectorSpectrum, join_id),
        (MMADetectorSpectrum, spectrum_id),
        (MMADetector, detector_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_mmadetector_time_interval(public_group, user):
    detector = MMADetector(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:8],
        type="gravitational-wave",
        fixed_location=True,
    )
    DBSession.add(detector)
    DBSession.commit()
    detector_id = detector.id

    time_interval = MMADetectorTimeInterval(
        detector_id=detector_id,
        owner_id=user.id,
    )
    DBSession.add(time_interval)
    DBSession.commit()
    time_interval_id = time_interval.id

    join = GroupMMADetectorTimeInterval(
        group_id=public_group.id,
        mmadetectortimeinterval_id=time_interval_id,
    )
    DBSession.add(join)
    DBSession.commit()
    join_id = join.id

    yield join

    for model, ident in (
        (GroupMMADetectorTimeInterval, join_id),
        (MMADetectorTimeInterval, time_interval_id),
        (MMADetector, detector_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_obj_analysis(public_group, public_source, user):
    # Inline parent: AnalysisService required by ObjAnalysis (analysis_service_id).
    analysis_service = AnalysisService(
        name=str(uuid.uuid4()),
        display_name="Test Analysis Service",
        url="http://localhost:5000/analysis/test_service",
        authentication_type="none",
        analysis_type="lightcurve_fitting",
        input_data_types=[],
    )
    DBSession.add(analysis_service)
    DBSession.commit()
    analysis_service_id = analysis_service.id

    # Inline parent: ObjAnalysis. Scope to public_group so row-level read is
    # meaningful (members of public_group can read; outsiders cannot).
    # WebhookMixin requires handled_by_url and status (no defaults).
    obj_analysis = ObjAnalysis(
        obj_id=public_source.id,
        author_id=user.id,
        analysis_service_id=analysis_service_id,
        handled_by_url="/api/webhook/obj_analysis",
        status="completed",
    )
    DBSession.add(obj_analysis)
    DBSession.commit()
    obj_analysis_id = obj_analysis.id

    group_obj_analysis = GroupObjAnalysis(
        group_id=public_group.id,
        obj_analyse_id=obj_analysis_id,
    )
    DBSession.add(group_obj_analysis)
    DBSession.commit()
    group_obj_analysis_id = group_obj_analysis.id

    yield group_obj_analysis

    for model, ident in (
        (GroupObjAnalysis, group_obj_analysis_id),
        (ObjAnalysis, obj_analysis_id),
        (AnalysisService, analysis_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_obj_tag(public_source, public_group, user):
    option = ObjTagOption(name=str(uuid.uuid4()))
    DBSession.add(option)
    DBSession.commit()
    option_id = option.id
    tag = ObjTag(
        objtagoption_id=option_id,
        obj_id=public_source.id,
        author_id=user.id,
    )
    DBSession.add(tag)
    DBSession.commit()
    tag_id = tag.id
    group_obj_tag = GroupObjTag(
        group_id=public_group.id,
        obj_tag_id=tag_id,
    )
    DBSession.add(group_obj_tag)
    DBSession.commit()
    group_obj_tag_id = group_obj_tag.id
    yield group_obj_tag
    for model, ident in (
        (GroupObjTag, group_obj_tag_id),
        (ObjTag, tag_id),
        (ObjTagOption, option_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_photometric_series(user, public_source, public_group):
    # Build an instrument (with its telescope) inline; teardown handled below.
    instrument = InstrumentFactory()

    # Minimal valid photometric data: needs an mjd column and a flux/mag column.
    n = 10
    df = pd.DataFrame(
        {
            "mjd": np.linspace(59000.0, 59000.0 + n - 1, n),
            "flux": np.random.uniform(100.0, 200.0, n),
            "fluxerr": np.random.uniform(1.0, 5.0, n),
        }
    )

    ps = PhotometricSeries(
        data=df,
        obj_id=public_source.id,
        instrument_id=instrument.id,
        owner_id=user.id,
        series_name="test_group_phot_series",
        series_obj_id=str(uuid.uuid4().int % 1_000_000),
        ra=np.round(np.random.uniform(0, 360), 3),
        dec=np.round(np.random.uniform(-90, 90), 3),
        exp_time=30.0,
        filter="ztfg",
        group_ids=[public_group.id],
        stream_ids=[],
        origin=uuid.uuid4().hex,
    )
    # Associate with public_group so the join row (GroupPhotometricSeries) is created.
    ps.groups = [public_group]

    filename = None
    try:
        DBSession().add(ps)
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()
        filename = ps.filename
    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        InstrumentFactory.teardown(instrument)
        raise e

    ps_id = ps.id

    # Fetch the join row created via the groups secondary relationship.
    join = (
        DBSession()
        .execute(
            sa.select(GroupPhotometricSeries).filter(
                GroupPhotometricSeries.group_id == public_group.id,
                GroupPhotometricSeries.photometric_serie_id == ps_id,
            )
        )
        .scalars()
        .first()
    )

    yield join

    # Teardown: delete the photometric series (cascades to the join row),
    # then remove the on-disk data file and the instrument/telescope.
    series = (
        DBSession()
        .execute(sa.select(PhotometricSeries).filter(PhotometricSeries.id == ps_id))
        .scalars()
        .first()
    )
    if series is not None:
        DBSession().delete(series)
        DBSession().commit()
    if filename is not None and os.path.isfile(filename):
        os.remove(filename)
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_group_public_release(public_group):
    release = PublicRelease(
        name=str(uuid.uuid4()),
        link_name=str(uuid.uuid4()),
        description="test release",
        options={},
    )
    DBSession.add(release)
    DBSession.commit()
    release_id = release.id

    group_public_release = GroupPublicRelease(
        group_id=public_group.id,
        publicrelease_id=release_id,
    )
    DBSession.add(group_public_release)
    DBSession.commit()
    group_public_release_id = group_public_release.id

    yield group_public_release

    join_obj = (
        DBSession()
        .execute(
            sa.select(GroupPublicRelease).filter(
                GroupPublicRelease.id == group_public_release_id
            )
        )
        .scalars()
        .first()
    )
    if join_obj is not None:
        DBSession().delete(join_obj)
        DBSession().commit()

    release_obj = (
        DBSession()
        .execute(sa.select(PublicRelease).filter(PublicRelease.id == release_id))
        .scalars()
        .first()
    )
    if release_obj is not None:
        DBSession().delete(release_obj)
        DBSession().commit()


@pytest.fixture()
def public_group_reminder(public_source, public_group, user):
    reminder = Reminder(
        text=str(uuid.uuid4()),
        obj_id=public_source.id,
        user_id=user.id,
        next_reminder=utcnow_naive(),
        reminder_delay=1.0,
        number_of_reminders=1,
        bot=False,
    )
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id

    group_reminder = GroupReminder(
        group_id=public_group.id,
        reminder_id=reminder_id,
    )
    DBSession.add(group_reminder)
    DBSession.commit()
    group_reminder_id = group_reminder.id

    yield group_reminder

    for model, ident in (
        (GroupReminder, group_reminder_id),
        (Reminder, reminder_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_reminder_on_earthquake(public_group, user):
    # Parent 1: an EarthquakeEvent (read defaults to public)
    earthquake = EarthquakeEvent(
        event_id=str(uuid.uuid4()),
        status="initial",
        sent_by_id=user.id,
    )
    DBSession.add(earthquake)
    DBSession.commit()
    earthquake_id = earthquake.id

    # Parent 2: a ReminderOnEarthquake, scoped to public_group and owned by user
    reminder = ReminderOnEarthquake(
        text=str(uuid.uuid4()),
        next_reminder=datetime.now(UTC),
        reminder_delay=1.0,
        number_of_reminders=1,
        bot=False,
        user_id=user.id,
        earthquake_id=earthquake_id,
    )
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id

    # The join row linking the Group to the ReminderOnEarthquake
    group_reminder = GroupReminderOnEarthquake(
        group_id=public_group.id,
        reminders_on_earthquake_id=reminder_id,
    )
    DBSession.add(group_reminder)
    DBSession.commit()
    group_reminder_id = group_reminder.id

    yield group_reminder

    for model, ident in (
        (GroupReminderOnEarthquake, group_reminder_id),
        (ReminderOnEarthquake, reminder_id),
        (EarthquakeEvent, earthquake_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_reminder_on_gcn(public_group, user):
    # Minimal GcnEvent (read is public by default; only dateobs + sent_by_id required,
    # all JSONB/array required cols have server_defaults so no parquet/localization needed).
    gcnevent = GcnEvent(
        dateobs=utcnow_naive(),
        trigger_id=str(uuid.uuid4().int)[:12],
        sent_by_id=user.id,
    )
    DBSession.add(gcnevent)
    DBSession.commit()
    gcnevent_id = gcnevent.id

    # ReminderOnGCN scoped to public_group so accessible_by_groups_members is meaningful;
    # user is the owner so update/delete (AccessibleIfUserMatches('user')) resolves for them.
    reminder = ReminderOnGCN(
        text=str(uuid.uuid4()),
        next_reminder=utcnow_naive() + timedelta(days=1),
        reminder_delay=1.0,
        number_of_reminders=1,
        bot=False,
        gcn_id=gcnevent_id,
        user_id=user.id,
    )
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id

    group_reminder = GroupReminderOnGCN(
        group_id=public_group.id,
        reminders_on_gcn_id=reminder_id,
    )
    DBSession.add(group_reminder)
    DBSession.commit()
    group_reminder_id = group_reminder.id

    yield group_reminder

    for model, ident in (
        (GroupReminderOnGCN, group_reminder_id),
        (ReminderOnGCN, reminder_id),
        (GcnEvent, gcnevent_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_reminder_on_shift(public_group, user):
    now = utcnow_naive()
    shift = Shift(
        name=str(uuid.uuid4()),
        start_date=now,
        end_date=now + timedelta(days=1),
        group_id=public_group.id,
    )
    DBSession.add(shift)
    DBSession.commit()
    shift_id = shift.id

    reminder = ReminderOnShift(
        text=str(uuid.uuid4()),
        bot=False,
        next_reminder=now + timedelta(days=1),
        reminder_delay=1.0,
        number_of_reminders=1,
        user_id=user.id,
        shift_id=shift_id,
    )
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id

    join = GroupReminderOnShift(
        group_id=public_group.id,
        reminders_on_shift_id=reminder_id,
    )
    DBSession.add(join)
    DBSession.commit()
    join_id = join.id

    yield join

    for model, ident in (
        (GroupReminderOnShift, join_id),
        (ReminderOnShift, reminder_id),
        (Shift, shift_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_reminder_on_spectrum(public_group, public_source, user):
    # Inline instrument (creates a telescope via SubFactory) for the Spectrum.
    instrument = InstrumentFactory()

    # Inline Spectrum associated with public_source / public_group.
    spectrum = Spectrum(
        wavelengths=[600.0, 650.0, 700.0],
        fluxes=[1.0, 1.5, 2.0],
        obj_id=public_source.id,
        observed_at=utcnow_naive(),
        type="source",
        instrument_id=instrument.id,
        owner_id=1,
        groups=[public_group],
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id

    # Inline ReminderOnSpectrum (the parent that carries row-level access),
    # scoped to public_group and authored by `user`.
    reminder = ReminderOnSpectrum(
        text=str(uuid.uuid4()),
        next_reminder=utcnow_naive() + timedelta(days=1),
        reminder_delay=1.0,
        number_of_reminders=1,
        bot=False,
        user_id=user.id,
        obj_id=public_source.id,
        spectrum_id=spectrum_id,
    )
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id

    # The actual join-model row mapping public_group -> reminder.
    group_reminder = GroupReminderOnSpectrum(
        group_id=public_group.id,
        reminders_on_spectr_id=reminder_id,
    )
    DBSession.add(group_reminder)
    DBSession.commit()
    group_reminder_id = group_reminder.id

    yield group_reminder

    for model, ident in (
        (GroupReminderOnSpectrum, group_reminder_id),
        (ReminderOnSpectrum, reminder_id),
        (Spectrum, spectrum_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_group_scan_report(public_group, user):
    report = ScanReport(
        author_id=user.id,
        options={},
        groups=[public_group],
    )
    DBSession.add(report)
    DBSession.commit()
    report_id = report.id
    group_scan_report = (
        DBSession()
        .execute(
            sa.select(GroupScanReport).filter(
                GroupScanReport.scanreport_id == report_id,
                GroupScanReport.group_id == public_group.id,
            )
        )
        .scalars()
        .first()
    )
    yield group_scan_report
    for model, ident in (
        (GroupScanReport, group_scan_report.id if group_scan_report else None),
        (ScanReport, report_id),
    ):
        if ident is None:
            continue
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_group_source_notification(public_group, public_source, user):
    # Parent 2: a SourceNotification owned by `user`, targeting public_source.
    # level="soft" avoids the SMS/Twilio branch in the after_insert listener;
    # email sends are disabled in the test environment.
    notification = models.SourceNotification(
        sent_by=user,
        source=public_source,
        level="soft",
        additional_notes=str(uuid.uuid4()),
    )
    DBSession().add(notification)
    DBSession().commit()
    notification_id = notification.id

    # Parent 1: public_group; link via the GroupSourceNotification join row.
    group_notification = models.GroupSourceNotification(
        group_id=public_group.id,
        sourcenotification_id=notification_id,
    )
    DBSession().add(group_notification)
    DBSession().commit()
    group_notification_id = group_notification.id

    yield group_notification

    join_row = (
        DBSession()
        .execute(
            sa.select(models.GroupSourceNotification).filter(
                models.GroupSourceNotification.id == group_notification_id
            )
        )
        .scalars()
        .first()
    )
    if join_row is not None:
        DBSession().delete(join_row)
        DBSession().commit()

    notif_row = (
        DBSession()
        .execute(
            sa.select(models.SourceNotification).filter(
                models.SourceNotification.id == notification_id
            )
        )
        .scalars()
        .first()
    )
    if notif_row is not None:
        DBSession().delete(notif_row)
        DBSession().commit()


@pytest.fixture()
def public_instrument_field():
    instrument = InstrumentFactory()
    field = InstrumentField(
        instrument_id=instrument.id,
        field_id=1,
        ra=30.0,
        dec=10.0,
        contour={},
        contour_summary={},
    )
    DBSession.add(field)
    DBSession.commit()
    field_id = field.id
    yield field
    row = (
        DBSession()
        .execute(sa.select(InstrumentField).filter(InstrumentField.id == field_id))
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_instrument_log():
    telescope = Telescope(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:10],
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        diameter=2.0,
        robotic=True,
        fixed_location=True,
    )
    DBSession.add(telescope)
    DBSession.commit()
    telescope_id = telescope.id

    instrument = Instrument(
        name=str(uuid.uuid4()),
        type="imager",
        band="Optical",
        telescope_id=telescope_id,
        filters=[],
    )
    DBSession.add(instrument)
    DBSession.commit()
    instrument_id = instrument.id

    instrument_log = InstrumentLog(
        instrument_id=instrument_id,
        start_date=datetime(2020, 1, 1, 0, 0, 0),
        end_date=datetime(2020, 1, 2, 0, 0, 0),
        log={},
    )
    DBSession.add(instrument_log)
    DBSession.commit()
    instrument_log_id = instrument_log.id

    yield instrument_log

    log = (
        DBSession()
        .execute(sa.select(InstrumentLog).filter(InstrumentLog.id == instrument_log_id))
        .scalars()
        .first()
    )
    if log is not None:
        DBSession().delete(log)
        DBSession().commit()

    instr = (
        DBSession()
        .execute(sa.select(Instrument).filter(Instrument.id == instrument_id))
        .scalars()
        .first()
    )
    if instr is not None:
        DBSession().delete(instr)
        DBSession().commit()

    tel = (
        DBSession()
        .execute(sa.select(Telescope).filter(Telescope.id == telescope_id))
        .scalars()
        .first()
    )
    if tel is not None:
        DBSession().delete(tel)
        DBSession().commit()


@pytest.fixture()
def public_instrument_sharing_service(public_group):
    # Create a Telescope (required parent for Instrument)
    telescope = models.Telescope(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4()),
        lat=33.3,
        lon=-116.8,
        elevation=1870.0,
        diameter=1.6,
    )
    DBSession.add(telescope)
    DBSession.commit()
    telescope_id = telescope.id

    # Create an Instrument hosted by that Telescope
    instrument = models.Instrument(
        name=str(uuid.uuid4()),
        type="imaging spectrograph",
        band="Optical",
        telescope_id=telescope_id,
        filters=["sdssg", "sdssr"],
    )
    DBSession.add(instrument)
    DBSession.commit()
    instrument_id = instrument.id

    # Create a SharingService and associate it with public_group so that
    # members of public_group can read it (read access is group-scoped).
    sharing_service = models.SharingService(name=str(uuid.uuid4()))
    DBSession.add(sharing_service)
    DBSession.commit()
    sharing_service_id = sharing_service.id

    sharing_service_group = models.SharingServiceGroup(
        sharing_service_id=sharing_service_id,
        group_id=public_group.id,
        owner=True,
    )
    DBSession.add(sharing_service_group)
    DBSession.commit()
    sharing_service_group_id = sharing_service_group.id

    # Create the join-model instance linking Instrument and SharingService
    instrument_sharing_service = models.InstrumentSharingService(
        instrument_id=instrument_id,
        sharing_service_id=sharing_service_id,
    )
    DBSession.add(instrument_sharing_service)
    DBSession.commit()
    instrument_sharing_service_id = instrument_sharing_service.id

    yield instrument_sharing_service

    for model, ident in (
        (models.InstrumentSharingService, instrument_sharing_service_id),
        (models.SharingServiceGroup, sharing_service_group_id),
        (models.SharingService, sharing_service_id),
        (models.Instrument, instrument_id),
        (models.Telescope, telescope_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_listing(public_source, user):
    listing = Listing(
        user_id=user.id,
        obj_id=public_source.id,
        list_name=str(uuid.uuid4()),
    )
    DBSession.add(listing)
    DBSession.commit()
    listing_id = listing.id
    yield listing
    row = (
        DBSession()
        .execute(sa.select(Listing).filter(Listing.id == listing_id))
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_localization(user):
    dateobs = utcnow_naive().replace(microsecond=0)

    gcnevent = GcnEvent(
        dateobs=dateobs,
        sent_by_id=user.id,
    )
    DBSession.add(gcnevent)
    DBSession.commit()

    localization = Localization(
        dateobs=dateobs,
        localization_name=str(uuid.uuid4()),
        sent_by_id=user.id,
        uniq=[4 * (4**29) + i for i in range(4)],
        probdensity=[1.0, 1.0, 1.0, 1.0],
    )
    DBSession.add(localization)
    DBSession.commit()
    localization_id = localization.id
    yield localization
    loc = (
        DBSession()
        .execute(sa.select(Localization).filter(Localization.id == localization_id))
        .scalars()
        .first()
    )
    if loc is not None:
        DBSession().delete(loc)
        DBSession().commit()
    event = (
        DBSession()
        .execute(sa.select(GcnEvent).filter(GcnEvent.dateobs == dateobs))
        .scalars()
        .first()
    )
    if event is not None:
        DBSession().delete(event)
        DBSession().commit()


@pytest.fixture()
def public_mmadetector():
    detector = MMADetector(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:8],
        type="gravitational-wave",
        lat=46.455,
        lon=-119.408,
        elevation=142.554,
        fixed_location=True,
    )
    DBSession.add(detector)
    DBSession.commit()
    detector_id = detector.id
    yield detector
    obj = (
        DBSession()
        .execute(sa.select(MMADetector).filter(MMADetector.id == detector_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_mmadetector_spectrum(public_group, user):
    detector = MMADetector(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:8],
        type="gravitational-wave",
        fixed_location=True,
    )
    DBSession.add(detector)
    DBSession.commit()
    detector_id = detector.id

    spectrum = MMADetectorSpectrum(
        frequencies=np.array([1.0, 2.0, 3.0]),
        amplitudes=np.array([1.0e-23, 2.0e-23, 3.0e-23]),
        start_time=utcnow_naive(),
        end_time=utcnow_naive() + timedelta(hours=1),
        detector_id=detector_id,
        owner_id=user.id,
        groups=[public_group],
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id
    yield spectrum
    for model, ident in (
        (MMADetectorSpectrum, spectrum_id),
        (MMADetector, detector_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_mmadetector_time_interval(public_group, user):
    detector = MMADetector(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4())[:8],
        type="gravitational-wave",
    )
    DBSession.add(detector)
    DBSession.commit()
    detector_id = detector.id

    time_interval = MMADetectorTimeInterval(
        detector_id=detector_id,
        owner_id=user.id,
        time_interval="[2020-01-01 00:00:00,2020-01-02 00:00:00]",
        groups=[public_group],
    )
    DBSession.add(time_interval)
    DBSession.commit()
    time_interval_id = time_interval.id
    yield time_interval
    for model, ident in (
        (MMADetectorTimeInterval, time_interval_id),
        (MMADetector, detector_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_obj_model(public_group):
    obj_id = str(uuid.uuid4())
    obj = Obj(
        id=obj_id,
        ra=10.0,
        dec=20.0,
        internal_key=str(uuid.uuid4()),
    )
    DBSession.add(obj)
    DBSession.commit()
    source = Source(obj_id=obj.id, group_id=public_group.id)
    DBSession.add(source)
    DBSession.commit()
    yield obj
    src = (
        DBSession()
        .execute(sa.select(Source).filter(Source.obj_id == obj_id))
        .scalars()
        .first()
    )
    if src is not None:
        DBSession().delete(src)
        DBSession().commit()
    row = DBSession().execute(sa.select(Obj).filter(Obj.id == obj_id)).scalars().first()
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_obj_analysis(public_source, public_group, user):
    analysis_service = AnalysisService(
        name=str(uuid.uuid4()),
        display_name="Test Analysis Service",
        url="http://localhost:5000/analysis/test_service",
        authentication_type="none",
        analysis_type="lightcurve_fitting",
        groups=[public_group],
    )
    DBSession.add(analysis_service)
    DBSession.commit()
    analysis_service_id = analysis_service.id

    analysis = ObjAnalysis(
        obj_id=public_source.id,
        author_id=user.id,
        analysis_service_id=analysis_service_id,
        _unique_id=str(uuid.uuid4()),
        show_parameters=False,
        show_plots=False,
        show_corner=False,
        handled_by_url="/api/webhook/obj_analysis",
        status="queued",
        token=str(uuid.uuid4()),
        groups=[public_group],
    )
    DBSession.add(analysis)
    DBSession.commit()
    analysis_id = analysis.id

    yield analysis

    for model, ident in (
        (ObjAnalysis, analysis_id),
        (AnalysisService, analysis_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_obj_tag_option():
    option = ObjTagOption(name=str(uuid.uuid4()))
    DBSession.add(option)
    DBSession.commit()
    option_id = option.id
    yield option
    obj = (
        DBSession()
        .execute(sa.select(ObjTagOption).filter(ObjTagOption.id == option_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_observation_plan_request(public_group, user):
    # Build a GcnEvent with an ingested Localization inline (needs HEALPix
    # localization data files shipped with the test suite).
    dateobs = utcnow_naive()
    notice_dict = {
        "notice_type": "Test",
        "notice_format": "Test",
        "stream": "Test",
        "dateobs": dateobs,
        "date": dateobs.strftime("%Y-%m-%d %H:%M:%S"),
        "content": bytes(1024),
        "has_localization": True,
        "localization_ingested": True,
    }
    localization_dict = {
        "localization_name": str(uuid.uuid4()),
        "localization_data_path": "data/localization_GW190814.parquet",
        "localization_tiles_data_path": "data/localizationtiles_GW190814.parquet",
        "properties": {"test": "test"},
        "tags": ["Test"],
    }
    gcnevent = GcnEventFactory(
        dateobs=dateobs,
        trigger_id=str(uuid.uuid4().int)[:9],
        aliases=[f"TEST#{uuid.uuid4().hex}"],
        gcn_notices=[notice_dict],
        properties={"test": "test"},
        localizations=[localization_dict],
    )
    localization = gcnevent.localizations[0]

    # Allocation scoped to public_group so row-level access is meaningful.
    allocation = AllocationFactory(
        group=public_group,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100,
    )

    request = ObservationPlanRequest(
        requester=user,
        last_modified_by=user,
        gcnevent_id=gcnevent.id,
        localization_id=localization.id,
        allocation_id=allocation.id,
        payload={},
        status="pending submission",
    )
    DBSession.add(request)
    DBSession.commit()
    request_id = request.id
    yield request
    row = (
        DBSession()
        .execute(
            sa.select(ObservationPlanRequest).filter(
                ObservationPlanRequest.id == request_id
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()
    AllocationFactory.teardown(allocation)
    GcnEventFactory.teardown(gcnevent)


@pytest.fixture()
def public_observation_plan_request_target_group(public_group, user):
    # --- Telescope + Instrument (inline parents) ---
    telescope = Telescope(
        name=f"Telescope_{uuid.uuid4().hex}",
        nickname=f"T_{uuid.uuid4().hex[:8]}",
        lat=33.3563,
        lon=-116.8650,
        elevation=1712.0,
        diameter=1.2,
        robotic=True,
    )
    DBSession.add(telescope)
    DBSession.commit()

    instrument = Instrument(
        name=f"Instrument_{uuid.uuid4().hex}",
        type="imaging spectrograph",
        band="Optical",
        telescope=telescope,
        filters=["sdssr"],
    )
    DBSession.add(instrument)
    DBSession.commit()

    # --- Allocation scoped to public_group so insiders can read it ---
    allocation = Allocation(
        instrument_id=instrument.id,
        group_id=public_group.id,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100.0,
    )
    DBSession.add(allocation)
    DBSession.commit()

    # --- GcnEvent + Localization (no external data files needed) ---
    dateobs = utcnow_naive()
    notice_dict = {
        "notice_type": "Test",
        "notice_format": "Test",
        "stream": str(uuid.uuid4().hex),
        "dateobs": dateobs,
        "date": dateobs,
        "content": bytes(1024),
        "has_localization": True,
        "localization_ingested": True,
    }
    localization_dict = {
        "localization_name": f"Localization_{uuid.uuid4().hex}",
        "tags": ["Test"],
    }
    gcnevent = GcnEventFactory(
        dateobs=dateobs,
        sent_by=user,
        gcn_notices=[notice_dict],
        localizations=[localization_dict],
    )
    localization = gcnevent.localizations[0]

    # --- ObservationPlanRequest (requester = user) ---
    request = ObservationPlanRequest(
        requester_id=user.id,
        gcnevent_id=gcnevent.id,
        localization_id=localization.id,
        allocation_id=allocation.id,
        payload={},
        status="pending submission",
    )
    DBSession.add(request)
    DBSession.commit()

    # --- The join row: couple the request with public_group ---
    target_group = ObservationPlanRequestTargetGroup(
        observationplanrequest_id=request.id,
        group_id=public_group.id,
    )
    DBSession.add(target_group)
    DBSession.commit()

    target_group_id = target_group.id
    request_id = request.id
    allocation_id = allocation.id
    instrument_id = instrument.id
    telescope_id = telescope.id

    yield target_group

    for model, ident in (
        (ObservationPlanRequestTargetGroup, target_group_id),
        (ObservationPlanRequest, request_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()

    GcnEventFactory.teardown(gcnevent)

    for model, ident in (
        (Allocation, allocation_id),
        (Instrument, instrument_id),
        (Telescope, telescope_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_phot_stat(public_source):
    phot_stat = (
        DBSession()
        .execute(sa.select(PhotStat).filter(PhotStat.obj_id == public_source.id))
        .scalars()
        .first()
    )
    if phot_stat is None:
        phot_stat = PhotStat(obj_id=public_source.id)
        phot_stat.num_obs_global = 0
        phot_stat.num_det_global = 0
        phot_stat.num_det_no_forced_phot_global = 0
        DBSession.add(phot_stat)
        DBSession.commit()
    phot_stat_id = phot_stat.id
    yield phot_stat
    row = (
        DBSession()
        .execute(sa.select(PhotStat).filter(PhotStat.id == phot_stat_id))
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_photometric_series(user, public_source, public_group):
    # Build an instrument (with its own telescope) inline; PhotometricSeries
    # requires an instrument_id and uses instrument.name / telescope.nickname.
    instrument = InstrumentFactory()
    instrument_id = instrument.id

    # Build the photometric data inline as a pandas DataFrame. The constructor
    # runs verify_data, calc_flux_mag and calc_stats off of this.
    number = 20
    df = pd.DataFrame(
        {
            "mjd": np.sort(np.random.uniform(59000, 60000, number)),
            "flux": np.random.uniform(15, 16, number),
        }
    )

    data = {
        "obj_id": public_source.id,
        "data": df,
        "instrument_id": instrument_id,
        "owner_id": user.id,
        "series_name": f"series_{uuid.uuid4().hex}",
        "series_obj_id": str(np.random.randint(0, 1_000_000)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 30.0,
        "filter": "ztfg",
        # associate with public_group so row-level read access is meaningful
        "group_ids": [public_group.id, user.single_user_group.id],
        "stream_ids": [],
        "origin": uuid.uuid4().hex,
        "channel": "A",
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        # save_data() writes the HDF5 file to disk and sets ps.filename, which
        # the before_insert event listener requires to be non-None.
        ps.save_data(temp=True)
        DBSession().commit()
        ps.move_temp_data()
    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        InstrumentFactory.teardown(instrument)
        raise e

    ps_id = ps.id
    filename = ps.filename

    yield ps

    # tear down by id; no-op if already gone
    row = (
        DBSession()
        .execute(sa.select(PhotometricSeries).filter(PhotometricSeries.id == ps_id))
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()
    if filename is not None and os.path.isfile(filename):
        os.remove(filename)
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_photometry_validation(public_source, user):
    photometry = public_source.photometry[0]
    validation = PhotometryValidation(
        photometry_id=photometry.id,
        validator_id=user.id,
        validated=True,
        explanation=str(uuid.uuid4()),
        notes=str(uuid.uuid4()),
    )
    DBSession.add(validation)
    DBSession.commit()
    validation_id = validation.id
    yield validation
    obj = (
        DBSession()
        .execute(
            sa.select(PhotometryValidation).filter(
                PhotometryValidation.id == validation_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_recurring_api(user):
    recurring_api = RecurringAPI(
        owner_id=user.id,
        endpoint=f"api/{uuid.uuid4().hex}",
        payload={},
        method="GET",
        next_call=utcnow_naive(),
        call_delay=1.0,
        number_of_retries=10,
        active=True,
    )
    DBSession.add(recurring_api)
    DBSession.commit()
    recurring_api_id = recurring_api.id
    yield recurring_api
    obj = (
        DBSession()
        .execute(sa.select(RecurringAPI).filter(RecurringAPI.id == recurring_api_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_reminder(public_source, public_group, user):
    reminder = Reminder(
        text=str(uuid.uuid4()),
        bot=False,
        next_reminder=utcnow_naive(),
        reminder_delay=1.0,
        number_of_reminders=1,
        obj_id=public_source.id,
        user_id=user.id,
        groups=[public_group],
    )
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id
    yield reminder
    row = (
        DBSession()
        .execute(sa.select(Reminder).filter(Reminder.id == reminder_id))
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_reminder_on_earthquake(public_group, user):
    earthquake = EarthquakeEvent(
        event_id=str(uuid.uuid4()),
        status="initial",
        sent_by_id=user.id,
    )
    DBSession.add(earthquake)
    DBSession.commit()
    earthquake_id = earthquake.id

    reminder = ReminderOnEarthquake(
        text="test reminder " + str(uuid.uuid4()),
        bot=False,
        next_reminder=utcnow_naive() + timedelta(days=1),
        reminder_delay=1.0,
        number_of_reminders=1,
        user_id=user.id,
        earthquake_id=earthquake_id,
        groups=[public_group],
    )
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id

    yield reminder

    reminder_obj = (
        DBSession()
        .execute(
            sa.select(ReminderOnEarthquake).filter(
                ReminderOnEarthquake.id == reminder_id
            )
        )
        .scalars()
        .first()
    )
    if reminder_obj is not None:
        DBSession().delete(reminder_obj)
        DBSession().commit()

    earthquake_obj = (
        DBSession()
        .execute(sa.select(EarthquakeEvent).filter(EarthquakeEvent.id == earthquake_id))
        .scalars()
        .first()
    )
    if earthquake_obj is not None:
        DBSession().delete(earthquake_obj)
        DBSession().commit()


@pytest.fixture()
def public_reminder_on_gcn(public_group, user):
    dateobs = datetime.now()
    gcnevent = GcnEvent(
        dateobs=dateobs,
        trigger_id=uuid.uuid4().hex,
        sent_by_id=user.id,
    )
    DBSession.add(gcnevent)
    DBSession.commit()
    gcnevent_id = gcnevent.id

    reminder = ReminderOnGCN(
        text=str(uuid.uuid4()),
        bot=False,
        next_reminder=datetime.now() + timedelta(days=1),
        reminder_delay=1.0,
        number_of_reminders=1,
        user_id=user.id,
        gcn_id=gcnevent_id,
    )
    reminder.groups = [public_group]
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id

    yield reminder

    for model, ident in ((ReminderOnGCN, reminder_id), (GcnEvent, gcnevent_id)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_reminder_on_shift(public_group, user):
    shift = Shift(
        name=str(uuid.uuid4()),
        start_date=utcnow_naive(),
        end_date=utcnow_naive() + timedelta(days=1),
        group_id=public_group.id,
    )
    DBSession.add(shift)
    DBSession.commit()
    shift_id = shift.id

    reminder = ReminderOnShift(
        text=str(uuid.uuid4()),
        next_reminder=utcnow_naive() + timedelta(days=1),
        reminder_delay=1.0,
        number_of_reminders=1,
        bot=False,
        shift_id=shift_id,
        user_id=user.id,
    )
    reminder.groups = [public_group]
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id
    yield reminder
    for model, ident in ((ReminderOnShift, reminder_id), (Shift, shift_id)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_reminder_on_spectrum(public_source, public_group, user):
    instrument = InstrumentFactory()
    spectrum = Spectrum(
        obj_id=public_source.id,
        observed_at=utcnow_naive(),
        wavelengths=[1.0, 2.0, 3.0],
        fluxes=[1.0, 2.0, 3.0],
        instrument_id=instrument.id,
        type="source",
        owner_id=user.id,
        groups=[public_group],
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id

    reminder = ReminderOnSpectrum(
        text=str(uuid.uuid4()),
        next_reminder=utcnow_naive() + timedelta(days=1),
        reminder_delay=1.0,
        number_of_reminders=1,
        bot=False,
        obj_id=public_source.id,
        spectrum_id=spectrum_id,
        user_id=user.id,
        groups=[public_group],
    )
    DBSession.add(reminder)
    DBSession.commit()
    reminder_id = reminder.id

    yield reminder

    for model, ident in (
        (ReminderOnSpectrum, reminder_id),
        (Spectrum, spectrum_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_scan_report(public_group, user):
    report = ScanReport(
        author_id=user.id,
        options={},
        groups=[public_group],
    )
    DBSession.add(report)
    DBSession.commit()
    report_id = report.id
    yield report
    obj = (
        DBSession()
        .execute(sa.select(ScanReport).filter(ScanReport.id == report_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_scan_report_item(public_source, public_group, user):
    scan_report = ScanReport(
        author_id=user.id,
        options={},
        groups=[public_group],
    )
    DBSession.add(scan_report)
    DBSession.commit()
    scan_report_id = scan_report.id

    item = ScanReportItem(
        obj_id=public_source.id,
        scan_report_id=scan_report_id,
        data={},
    )
    DBSession.add(item)
    DBSession.commit()
    item_id = item.id

    yield item

    for model, ident in ((ScanReportItem, item_id), (ScanReport, scan_report_id)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_sharing_service(public_group):
    sharing_service = SharingService(
        name=str(uuid.uuid4()),
        acknowledgments="",
        testing=True,
        enable_sharing_with_hermes=False,
        enable_sharing_with_tns=True,
    )
    DBSession.add(sharing_service)
    DBSession.commit()
    sharing_service_id = sharing_service.id

    # Link the sharing service to public_group as an owner so that members of
    # public_group (user, group_admin_user) get read AND update/delete access.
    sharing_service_group = SharingServiceGroup(
        sharing_service_id=sharing_service_id,
        group_id=public_group.id,
        owner=True,
        auto_share_to_tns=False,
        auto_share_to_hermes=False,
        auto_sharing_allow_bots=False,
    )
    DBSession.add(sharing_service_group)
    DBSession.commit()
    sharing_service_group_id = sharing_service_group.id

    yield sharing_service

    for model, ident in (
        (SharingServiceGroup, sharing_service_group_id),
        (SharingService, sharing_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_sharing_service_coauthor(public_group, user):
    sharing_service = SharingService(
        name=str(uuid.uuid4()),
    )
    DBSession.add(sharing_service)
    DBSession.commit()
    sharing_service_id = sharing_service.id

    sharing_service_group = SharingServiceGroup(
        sharing_service_id=sharing_service_id,
        group_id=public_group.id,
        owner=True,
    )
    DBSession.add(sharing_service_group)
    DBSession.commit()
    sharing_service_group_id = sharing_service_group.id

    coauthor = SharingServiceCoauthor(
        sharing_service_id=sharing_service_id,
        user_id=user.id,
    )
    DBSession.add(coauthor)
    DBSession.commit()
    coauthor_id = coauthor.id
    yield coauthor
    for model, ident in (
        (SharingServiceCoauthor, coauthor_id),
        (SharingServiceGroup, sharing_service_group_id),
        (SharingService, sharing_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_sharing_service_group(public_group):
    sharing_service = SharingService(name=str(uuid.uuid4()))
    DBSession.add(sharing_service)
    DBSession.commit()
    sharing_service_id = sharing_service.id

    sharing_service_group = SharingServiceGroup(
        sharing_service_id=sharing_service_id,
        group_id=public_group.id,
        owner=True,
        auto_share_to_tns=False,
        auto_share_to_hermes=False,
        auto_sharing_allow_bots=False,
    )
    DBSession.add(sharing_service_group)
    DBSession.commit()
    sharing_service_group_id = sharing_service_group.id
    yield sharing_service_group
    for model, ident in (
        (SharingServiceGroup, sharing_service_group_id),
        (SharingService, sharing_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_sharing_service_group_auto_publisher(public_group, user):
    # ensure the user is a member of public_group so a GroupUser row exists
    if public_group not in user.groups:
        user.groups.append(public_group)
        DBSession().commit()

    group_user = (
        DBSession()
        .execute(
            sa.select(GroupUser).filter(
                GroupUser.group_id == public_group.id,
                GroupUser.user_id == user.id,
            )
        )
        .scalars()
        .first()
    )

    sharing_service = SharingService(name=str(uuid.uuid4()))
    DBSession().add(sharing_service)
    DBSession().commit()
    sharing_service_id = sharing_service.id

    sharing_service_group = SharingServiceGroup(
        sharing_service_id=sharing_service_id,
        group_id=public_group.id,
        owner=True,
    )
    DBSession().add(sharing_service_group)
    DBSession().commit()
    sharing_service_group_id = sharing_service_group.id

    auto_publisher = SharingServiceGroupAutoPublisher(
        sharing_service_group_id=sharing_service_group_id,
        group_user_id=group_user.id,
    )
    DBSession().add(auto_publisher)
    DBSession().commit()
    auto_publisher_id = auto_publisher.id

    yield auto_publisher

    # teardown auto_publisher
    obj = (
        DBSession()
        .execute(
            sa.select(SharingServiceGroupAutoPublisher).filter(
                SharingServiceGroupAutoPublisher.id == auto_publisher_id
            )
        )
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()

    # teardown sharing_service_group
    ssg = (
        DBSession()
        .execute(
            sa.select(SharingServiceGroup).filter(
                SharingServiceGroup.id == sharing_service_group_id
            )
        )
        .scalars()
        .first()
    )
    if ssg is not None:
        DBSession().delete(ssg)
        DBSession().commit()

    # teardown sharing_service
    ss = (
        DBSession()
        .execute(
            sa.select(SharingService).filter(SharingService.id == sharing_service_id)
        )
        .scalars()
        .first()
    )
    if ss is not None:
        DBSession().delete(ss)
        DBSession().commit()


@pytest.fixture()
def public_sharing_service_submission(public_group, public_source, user):
    sharing_service = SharingService(
        name=str(uuid.uuid4()),
    )
    DBSession.add(sharing_service)
    DBSession.commit()
    sharing_service_id = sharing_service.id

    sharing_service_group = SharingServiceGroup(
        sharing_service_id=sharing_service_id,
        group_id=public_group.id,
        owner=True,
    )
    DBSession.add(sharing_service_group)
    DBSession.commit()
    sharing_service_group_id = sharing_service_group.id

    submission = SharingServiceSubmission(
        sharing_service_id=sharing_service_id,
        obj_id=public_source.id,
        user_id=user.id,
        publish_to_tns=False,
        publish_to_hermes=False,
        archival=False,
        auto_submission=False,
    )
    DBSession.add(submission)
    DBSession.commit()
    submission_id = submission.id

    yield submission

    for model, ident in (
        (SharingServiceSubmission, submission_id),
        (SharingServiceGroup, sharing_service_group_id),
        (SharingService, sharing_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_shift(public_group):
    shift = Shift(
        name=str(uuid.uuid4()),
        description="test shift",
        start_date=utcnow_naive(),
        end_date=utcnow_naive() + timedelta(days=1),
        group_id=public_group.id,
    )
    DBSession.add(shift)
    DBSession.commit()
    shift_id = shift.id
    yield shift
    obj = (
        DBSession()
        .execute(sa.select(Shift).filter(Shift.id == shift_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_shift_user(public_group, user):
    shift = Shift(
        name=str(uuid.uuid4()),
        start_date=utcnow_naive(),
        end_date=utcnow_naive() + timedelta(days=1),
        group_id=public_group.id,
    )
    DBSession.add(shift)
    DBSession.commit()
    shift_id = shift.id
    shift_user = ShiftUser(
        shift_id=shift_id,
        user_id=user.id,
        admin=False,
        needs_replacement=False,
    )
    DBSession.add(shift_user)
    DBSession.commit()
    shift_user_id = shift_user.id
    yield shift_user
    for model, ident in ((ShiftUser, shift_user_id), (Shift, shift_id)):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_source_label(public_source, public_group, user):
    label = SourceLabel(
        obj_id=public_source.id,
        labeller_id=user.id,
        group_id=public_group.id,
    )
    DBSession.add(label)
    DBSession.commit()
    label_id = label.id
    yield label
    obj = (
        DBSession()
        .execute(sa.select(SourceLabel).filter(SourceLabel.id == label_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_source_view(public_source, user):
    source_view = SourceView(
        obj_id=public_source.id,
        username_or_token_id=user.username,
        is_token=False,
    )
    DBSession.add(source_view)
    DBSession.commit()
    source_view_id = source_view.id
    yield source_view
    row = (
        DBSession()
        .execute(sa.select(SourceView).filter(SourceView.id == source_view_id))
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_sources_confirmed_in_gcn(public_source, user):
    dateobs = utcnow_naive().replace(microsecond=0)

    gcnevent = GcnEvent(
        dateobs=dateobs,
        sent_by_id=user.id,
        trigger_id=str(uuid.uuid4())[:20],
    )
    DBSession.add(gcnevent)
    DBSession.commit()

    sources_confirmed_in_gcn = SourcesConfirmedInGCN(
        obj_id=public_source.id,
        dateobs=dateobs,
        confirmer_id=user.id,
        confirmed=True,
        explanation="test confirmation",
        notes="test notes",
    )
    DBSession.add(sources_confirmed_in_gcn)
    DBSession.commit()
    sources_confirmed_in_gcn_id = sources_confirmed_in_gcn.id
    gcnevent_dateobs = gcnevent.dateobs

    yield sources_confirmed_in_gcn

    row = (
        DBSession()
        .execute(
            sa.select(SourcesConfirmedInGCN).filter(
                SourcesConfirmedInGCN.id == sources_confirmed_in_gcn_id
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()

    event = (
        DBSession()
        .execute(sa.select(GcnEvent).filter(GcnEvent.dateobs == gcnevent_dateobs))
        .scalars()
        .first()
    )
    if event is not None:
        DBSession().delete(event)
        DBSession().commit()


@pytest.fixture()
def public_spatial_catalog():
    catalog = SpatialCatalog(catalog_name=str(uuid.uuid4()))
    DBSession.add(catalog)
    DBSession.commit()
    catalog_id = catalog.id
    yield catalog
    obj = (
        DBSession()
        .execute(sa.select(SpatialCatalog).filter(SpatialCatalog.id == catalog_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()


@pytest.fixture()
def public_spectrum_observer(public_source, public_group, user):
    # Build a Spectrum owned by `user`, associated with public_group so that
    # row-level read access is meaningful (user/group_admin_user = insiders,
    # user_group2 = outsider). SpectrumFactory creates its own instrument
    # (and reducer/observer Users) which are cleaned up by its teardown.
    spectrum = SpectrumFactory(
        obj_id=public_source.id,
        owner_id=user.id,
        groups=[public_group],
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id

    spectrum_observer = SpectrumObserver(
        spectr_id=spectrum_id,
        user_id=user.id,
    )
    DBSession.add(spectrum_observer)
    DBSession.commit()
    spectrum_observer_id = spectrum_observer.id

    yield spectrum_observer

    join_row = (
        DBSession()
        .execute(
            sa.select(SpectrumObserver).filter(
                SpectrumObserver.id == spectrum_observer_id
            )
        )
        .scalars()
        .first()
    )
    if join_row is not None:
        DBSession().delete(join_row)
        DBSession().commit()

    spectrum_row = (
        DBSession()
        .execute(sa.select(Spectrum).filter(Spectrum.id == spectrum_id))
        .scalars()
        .first()
    )
    if spectrum_row is not None:
        SpectrumFactory.teardown(spectrum_row)


@pytest.fixture()
def public_spectrum_pi(public_source, public_group, user):
    instrument = InstrumentFactory()
    instrument_id = instrument.id

    spectrum = Spectrum(
        obj_id=public_source.id,
        observed_at=datetime.now(),
        wavelengths=np.sort(1000 * np.random.random(20)),
        fluxes=1e-9 * np.random.random(20),
        instrument_id=instrument_id,
        owner_id=user.id,
        groups=[public_group],
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id

    spectrum_pi = SpectrumPI(
        spectr_id=spectrum_id,
        user_id=user.id,
        external_pi=str(uuid.uuid4()),
    )
    DBSession.add(spectrum_pi)
    DBSession.commit()
    spectrum_pi_id = spectrum_pi.id

    yield spectrum_pi

    for model, ident in (
        (SpectrumPI, spectrum_pi_id),
        (Spectrum, spectrum_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()
    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_spectrum_reducer(public_source, public_group, user):
    # Build an Instrument (and its Telescope) inline via the factory.
    instrument = InstrumentFactory()

    # Create a Spectrum owned by `user`, attached to the public source's obj
    # and visible to public_group, so that:
    #   - read (accessible_by_groups_members of the spectrum) makes
    #     public_group members insiders;
    #   - create/update/delete (AccessibleIfUserMatches("spectrum.owner"))
    #     resolves to `user`.
    spectrum = Spectrum(
        obj_id=public_source.id,
        instrument_id=instrument.id,
        wavelengths=np.sort(1000 * np.random.random(20)),
        fluxes=1e-9 * np.random.random(20),
        observed_at=datetime.now(),
        owner_id=user.id,
        groups=[public_group],
    )
    DBSession.add(spectrum)
    DBSession.commit()
    spectrum_id = spectrum.id

    reducer = SpectrumReducer(spectr_id=spectrum_id, user_id=user.id)
    DBSession.add(reducer)
    DBSession.commit()
    reducer_id = reducer.id

    yield reducer

    obj = (
        DBSession()
        .execute(sa.select(SpectrumReducer).filter(SpectrumReducer.id == reducer_id))
        .scalars()
        .first()
    )
    if obj is not None:
        DBSession().delete(obj)
        DBSession().commit()

    spec = (
        DBSession()
        .execute(sa.select(Spectrum).filter(Spectrum.id == spectrum_id))
        .scalars()
        .first()
    )
    if spec is not None:
        DBSession().delete(spec)
        DBSession().commit()

    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_stream_invitation(public_stream, user):
    # Look up the "Full user" Role required by the NOT NULL role_id column.
    role = DBSession().scalars(sa.select(Role).where(Role.id == "Full user")).first()
    # Invitation has several nullable=False columns: token, role_id,
    # admin_for_groups, can_save_to_groups, used. Fill them all.
    # NOTE: Invitation fires an after_insert listener that sends an email; the
    # test suite sets invitations.disable_emailing so it only logs instead.
    invitation = Invitation(
        token=str(uuid.uuid4()),
        role=role,
        admin_for_groups=[False],
        can_save_to_groups=[True],
        user_email="user@email.com",
        invited_by=user,
        used=False,
        streams=[public_stream],
    )
    DBSession.add(invitation)
    DBSession.commit()
    invitation_id = invitation.id

    # The streams relationship write created the StreamInvitation join row;
    # fetch it so tests can exercise row-level access control on it.
    stream_invitation = (
        DBSession()
        .execute(
            sa.select(StreamInvitation).filter(
                StreamInvitation.stream_id == public_stream.id,
                StreamInvitation.invitation_id == invitation_id,
            )
        )
        .scalars()
        .first()
    )
    yield stream_invitation

    # Deleting the parent Invitation cascades to the join row (ondelete=CASCADE).
    row = (
        DBSession()
        .execute(sa.select(Invitation).filter(Invitation.id == invitation_id))
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()


@pytest.fixture()
def public_stream_photometric_series(
    public_group, public_stream, public_source, user, group_admin_user
):
    # Make `user` and `group_admin_user` members of the stream so that
    # row-level access (create requires stream membership; read requires the
    # Stream to be readable) is meaningful. `user_group2` is left out -> outsider.
    for u in (user, group_admin_user):
        if u not in public_stream.users:
            public_stream.users.append(u)
    DBSession().add(public_stream)
    DBSession().commit()

    # Build an instrument (and its telescope) inline.
    instrument = InstrumentFactory()
    instrument_id = instrument.id

    # Minimal valid photometric-series dataframe: needs an mjd column and a
    # flux (or mag) column.
    number = 10
    df = pd.DataFrame(
        {
            "mjd": np.linspace(59000.0, 59001.0, number),
            "flux": np.random.uniform(100.0, 200.0, number),
        }
    )
    data = {
        "obj_id": public_source.id,
        "data": df,
        "instrument_id": instrument_id,
        "owner_id": user.id,
        "series_name": f"test_series_{uuid.uuid4().hex}",
        "series_obj_id": str(np.random.randint(0, 1e6)),
        "ra": np.round(np.random.uniform(0, 360), 3),
        "dec": np.round(np.random.uniform(-90, 90), 3),
        "exp_time": 30.0,
        "filter": "ztfg",
        # associate the PhotometricSeries with public_group/public_stream so it
        # is readable by insiders (read = groups_members | streams_members | owner).
        "group_ids": [public_group.id, user.single_user_group.id],
        "stream_ids": [public_stream.id],
        "origin": uuid.uuid4().hex,
        "channel": "A",
    }
    ps = PhotometricSeries(**data)

    try:
        DBSession().add(ps)
        ps.save_data(temp=True)  # generates a filename (required by before_insert)
        DBSession().commit()
        ps.move_temp_data()
    except Exception as e:
        DBSession().rollback()
        ps.delete_data(temp=True)
        InstrumentFactory.teardown(instrument)
        raise e

    ps_id = ps.id
    filename = ps.filename

    # Create the join row coupling the Stream and the PhotometricSeries.
    join = StreamPhotometricSeries(
        stream_id=public_stream.id,
        photometric_serie_id=ps_id,
    )
    DBSession().add(join)
    DBSession().commit()
    join_id = join.id

    yield join

    # tear down: join row, photometric series (+ data file), then instrument.
    row = (
        DBSession()
        .execute(
            sa.select(StreamPhotometricSeries).filter(
                StreamPhotometricSeries.id == join_id
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()

    series = (
        DBSession()
        .execute(sa.select(PhotometricSeries).filter(PhotometricSeries.id == ps_id))
        .scalars()
        .first()
    )
    if series is not None:
        DBSession().delete(series)
        DBSession().commit()
    if filename is not None and os.path.isfile(filename):
        os.remove(filename)

    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_stream_photometry(public_stream, public_source):
    # StreamPhotometry is a join_model coupling Stream and Photometry.
    # We build a Photometry inline (with its own Instrument), associate it with
    # public_stream so that stream-members can read it, then link it to the
    # stream via StreamPhotometry.

    instrument = InstrumentFactory()
    instrument_id = instrument.id

    photometry = Photometry(
        obj_id=public_source.id,
        instrument_id=instrument_id,
        owner_id=1,
        mjd=58000.0,
        flux=12.34,
        fluxerr=0.56,
        filter="ztfg",
        origin=str(uuid.uuid4()),
        upload_id=str(uuid.uuid4()),
    )
    DBSession().add(photometry)
    DBSession().commit()
    photometry_id = photometry.id

    stream_photometry = StreamPhotometry(
        stream_id=public_stream.id, photometr_id=photometry_id
    )
    DBSession().add(stream_photometry)
    DBSession().commit()
    stream_photometry_id = stream_photometry.id

    yield stream_photometry

    sp = (
        DBSession()
        .execute(
            sa.select(StreamPhotometry).filter(
                StreamPhotometry.id == stream_photometry_id
            )
        )
        .scalars()
        .first()
    )
    if sp is not None:
        DBSession().delete(sp)
        DBSession().commit()

    phot = (
        DBSession()
        .execute(sa.select(Photometry).filter(Photometry.id == photometry_id))
        .scalars()
        .first()
    )
    if phot is not None:
        DBSession().delete(phot)
        DBSession().commit()

    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_stream_sharing_service(public_stream, public_group):
    # Create a SharingService inline (parent #2 of the join row).
    sharing_service = SharingService(name=str(uuid.uuid4()))
    DBSession.add(sharing_service)
    DBSession.commit()
    sharing_service_id = sharing_service.id

    # Associate the SharingService with public_group so that members of
    # public_group can read it (SharingService.read is scoped via
    # SharingServiceGroup -> group membership). This makes the join row's
    # read access meaningful for insiders/outsiders.
    sharing_service_group = SharingServiceGroup(
        sharing_service_id=sharing_service_id,
        group_id=public_group.id,
        owner=True,
    )
    DBSession.add(sharing_service_group)
    DBSession.commit()
    sharing_service_group_id = sharing_service_group.id

    # The actual join row mapping the Stream to the SharingService.
    join = StreamSharingService(
        stream_id=public_stream.id,
        sharing_service_id=sharing_service_id,
    )
    DBSession.add(join)
    DBSession.commit()
    join_id = join.id

    yield join

    for model, ident in (
        (StreamSharingService, join_id),
        (SharingServiceGroup, sharing_service_group_id),
        (SharingService, sharing_service_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_survey_efficiency_for_observation_plan(public_group, user):
    """A SurveyEfficiencyForObservationPlan tied to public_group.

    Builds the full parent chain inline: Telescope + Instrument (factories),
    an Allocation on public_group, a GcnEvent, a minimal Localization,
    an ObservationPlanRequest, and an EventObservationPlan. The survey
    efficiency analysis is shared with public_group so that members of
    public_group (user, group_admin_user) are insiders and members of
    public_group2 only (user_group2) are outsiders.
    """

    dateobs = utcnow_naive().replace(microsecond=0)

    # Telescope + Instrument via existing factories
    telescope = TelescopeFactory(
        name=f"Telescope_{uuid.uuid4().hex}",
        nickname=f"T_{uuid.uuid4().hex[:8]}",
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        diameter=1.0,
    )
    instrument = InstrumentFactory(
        name=f"Instrument_{uuid.uuid4().hex}",
        type="imager",
        band="Optical",
        telescope=telescope,
        filters=["ztfg"],
    )

    # Allocation on public_group (drives Allocation/ObservationPlanRequest read)
    allocation = Allocation(
        instrument_id=instrument.id,
        group_id=public_group.id,
        pi=str(uuid.uuid4()),
        proposal_id=str(uuid.uuid4()),
        hours_allocated=100.0,
        types=["triggered"],
    )
    DBSession.add(allocation)
    DBSession.commit()

    # GcnEvent (dateobs is the natural key referenced by Localization)
    gcnevent = GcnEvent(dateobs=dateobs, sent_by_id=user.id)
    DBSession.add(gcnevent)
    DBSession.commit()

    # Minimal multiresolution HEALPix localization (no external files needed)
    localization = Localization(
        sent_by_id=user.id,
        dateobs=dateobs,
        localization_name=f"loc_{uuid.uuid4().hex}",
        uniq=[4 * 512**2],
        probdensity=[1.0],
    )
    DBSession.add(localization)
    DBSession.commit()

    # ObservationPlanRequest
    plan_request = ObservationPlanRequest(
        requester_id=user.id,
        gcnevent_id=gcnevent.id,
        localization_id=localization.id,
        allocation_id=allocation.id,
        payload={},
        status="complete",
    )
    DBSession.add(plan_request)
    DBSession.commit()

    # EventObservationPlan (read defaults to public via BaseMixin)
    observation_plan = EventObservationPlan(
        observation_plan_request_id=plan_request.id,
        instrument_id=instrument.id,
        dateobs=dateobs,
        plan_name=f"plan_{uuid.uuid4().hex}",
        status="complete",
    )
    DBSession.add(observation_plan)
    DBSession.commit()

    # The SurveyEfficiencyForObservationPlan itself, shared with public_group
    survey_efficiency = SurveyEfficiencyForObservationPlan(
        requester_id=user.id,
        observation_plan_id=observation_plan.id,
        payload={},
        status="complete",
        groups=[public_group],
    )
    DBSession.add(survey_efficiency)
    DBSession.commit()

    survey_efficiency_id = survey_efficiency.id
    observation_plan_id = observation_plan.id
    plan_request_id = plan_request.id
    localization_id = localization.id
    gcnevent_id = gcnevent.id
    allocation_id = allocation.id

    yield survey_efficiency

    for model, ident in (
        (SurveyEfficiencyForObservationPlan, survey_efficiency_id),
        (EventObservationPlan, observation_plan_id),
        (ObservationPlanRequest, plan_request_id),
        (Localization, localization_id),
        (GcnEvent, gcnevent_id),
        (Allocation, allocation_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()

    InstrumentFactory.teardown(instrument)


@pytest.fixture()
def public_survey_efficiency_for_observations(public_group, user):
    # Parent GcnEvent (read is public by default)
    gcnevent = GcnEventFactory(sent_by=user)
    dateobs = gcnevent.dateobs

    # Parent Localization, keyed to the GcnEvent's dateobs. uniq/probdensity
    # are nullable=False but empty arrays are valid (no skymap file needed).
    localization = Localization(
        sent_by_id=user.id,
        dateobs=dateobs,
        localization_name=str(uuid.uuid4().hex),
        uniq=[],
        probdensity=[],
        contour={},
    )
    DBSession.add(localization)
    DBSession.commit()

    # Parent Instrument (+ Telescope it needs)
    telescope = Telescope(
        name=str(uuid.uuid4()),
        nickname=str(uuid.uuid4()),
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        diameter=1.0,
    )
    DBSession.add(telescope)
    DBSession.commit()
    instrument = Instrument(
        name=f"ZTF_{uuid.uuid4().hex}",
        type="imager",
        band="Optical",
        telescope=telescope,
        filters=["ztfg", "ztfr", "ztfi"],
    )
    DBSession.add(instrument)
    DBSession.commit()

    analysis = SurveyEfficiencyForObservations(
        requester_id=user.id,
        gcnevent_id=gcnevent.id,
        localization_id=localization.id,
        instrument_id=instrument.id,
        payload={},
        status="pending submission",
        groups=[public_group],
    )
    DBSession.add(analysis)
    DBSession.commit()

    analysis_id = analysis.id
    localization_id = localization.id
    instrument_id = instrument.id
    telescope_id = telescope.id
    gcnevent_id = gcnevent.id

    yield analysis

    for model, ident in (
        (SurveyEfficiencyForObservations, analysis_id),
        (Localization, localization_id),
        (Instrument, instrument_id),
        (Telescope, telescope_id),
        (GcnEvent, gcnevent_id),
    ):
        row = (
            DBSession()
            .execute(sa.select(model).filter(model.id == ident))
            .scalars()
            .first()
        )
        if row is not None:
            DBSession().delete(row)
            DBSession().commit()


@pytest.fixture()
def public_user_invitation(public_group, user):
    # UserInvitation is a join_model("user_invitations", User, Invitation).
    # Its read/create policy is AccessibleIfRelatedRowsAreAccessible(user="read",
    # invitation="read"). User.read is public (always readable), while
    # Invitation.read = AccessibleIfUserMatches("invited_by"). The "invited_by"
    # relationship is resolved THROUGH this same user_invitations join row, so by
    # linking `user` as invited_by we make the invitation (and thus the join row)
    # readable only by `user` and system admins.
    role = (
        DBSession()
        .execute(sa.select(models.Role).filter(models.Role.id == "Full user"))
        .scalars()
        .first()
    )
    invitation = Invitation(
        token=str(uuid.uuid4()),
        role=role,
        admin_for_groups=[False],
        can_save_to_groups=[True],
        user_email="invitee@email.com",
        used=False,
        groups=[public_group],
        invited_by=user,
    )
    DBSession.add(invitation)
    DBSession.commit()
    invitation_id = invitation.id

    user_invitation = (
        DBSession()
        .execute(
            sa.select(UserInvitation).filter(
                UserInvitation.invitation_id == invitation_id,
                UserInvitation.user_id == user.id,
            )
        )
        .scalars()
        .first()
    )
    user_invitation_id = user_invitation.id
    yield user_invitation

    row = (
        DBSession()
        .execute(
            sa.select(UserInvitation).filter(UserInvitation.id == user_invitation_id)
        )
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()
    inv = (
        DBSession()
        .execute(sa.select(Invitation).filter(Invitation.id == invitation_id))
        .scalars()
        .first()
    )
    if inv is not None:
        DBSession().delete(inv)
        DBSession().commit()


@pytest.fixture()
def public_weather():
    telescope = TelescopeFactory(
        name=f"Weather Telescope_{uuid.uuid4()}",
        nickname=f"WT_{uuid.uuid4()}",
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        diameter=1.0,
        fixed_location=True,
    )
    telescope_id = telescope.id
    weather = Weather(
        telescope_id=telescope_id,
        weather_info={},
        retrieved_at=utcnow_naive(),
    )
    DBSession.add(weather)
    DBSession.commit()
    weather_id = weather.id
    yield weather
    row = (
        DBSession()
        .execute(sa.select(Weather).filter(Weather.id == weather_id))
        .scalars()
        .first()
    )
    if row is not None:
        DBSession().delete(row)
        DBSession().commit()
    TelescopeFactory.teardown(telescope_id)
