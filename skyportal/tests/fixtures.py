import datetime
import os
import pathlib
import random
import uuid
from itertools import cycle, islice
from tempfile import mkdtemp

import factory
import numpy as np
from sqlalchemy import inspect
from sqlalchemy.orm.exc import ObjectDeletedError

from baselayer.app.config import load_config
from baselayer.app.env import load_env
from baselayer.app.test_util import set_server_url
from skyportal.models import (
    DBSession,
    User,
    Group,
    Photometry,
    Spectrum,
    Stream,
    Instrument,
    Telescope,
    Obj,
    Comment,
    Annotation,
    Thumbnail,
    Filter,
    ObservingRun,
    ClassicalAssignment,
    Taxonomy,
    Classification,
    init_db,
    FollowupRequest,
    Allocation,
    Invitation,
    SourceNotification,
    UserNotification,
)

import tdtax

TMP_DIR = mkdtemp()
env, cfg = load_env()

print("Loading test configuration from _test_config.yaml")
basedir = pathlib.Path(os.path.dirname(__file__))
cfg = load_config([(basedir / "../../test_config.yaml").absolute()])
set_server_url(f'http://localhost:{cfg["ports.app"]}')
print("Setting test database to:", cfg["database"])
init_db(**cfg["database"])


def is_already_deleted(instance, table):
    """
    Helper function to check if a given ORM instance has already been deleted previously,
    either by earlier teardown functions or by a test itself through the API.
    """
    # If the instance is marked detached, that means it was deleted earlier in the
    # current transaction.
    if instance in DBSession() and inspect(instance).detached:
        return True

    if instance not in DBSession() or (
        instance in DBSession() and inspect(instance).expired
    ):
        try:
            return (
                DBSession().query(table).filter(table.id == instance.id).first() is None
            )
        except ObjectDeletedError:
            # If instance was deleted by the test, it would have taken place in
            # another transaction and thus undiscovered until the exception here
            return True

    # If the instance is in the session and has not been detached (deleted + committed)
    # then it still requires some teardown actions.
    return False


class BaseMeta:
    sqlalchemy_session = DBSession()
    sqlalchemy_session_persistence = 'commit'


class TelescopeFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Telescope

    name = factory.LazyFunction(lambda: f'Palomar 48 inch_{uuid.uuid4().hex}')
    nickname = factory.LazyFunction(lambda: f'P48_{uuid.uuid4().hex}')
    lat = 33.3563
    lon = -116.8650
    elevation = 1712.0
    diameter = 1.2
    robotic = True

    @staticmethod
    def teardown(telescope_id):
        telescope = (
            DBSession().query(Telescope).filter(Telescope.id == telescope_id).first()
        )
        if telescope is not None:
            DBSession().delete(telescope)
            DBSession().commit()


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = User

    username = factory.LazyFunction(lambda: uuid.uuid4().hex)
    contact_email = factory.LazyFunction(lambda: f'{uuid.uuid4().hex[:10]}@gmail.com')
    first_name = factory.LazyFunction(lambda: f'{uuid.uuid4().hex[:4]}')
    last_name = factory.LazyFunction(lambda: f'{uuid.uuid4().hex[:4]}')

    @factory.post_generation
    def roles(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for role in extracted:
                obj.roles.append(role)
                DBSession().add(obj)
                DBSession().commit()

    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for group in extracted:
                obj.groups.append(group)
                DBSession().add(obj)
                DBSession().commit()

        # always add the sitewide group
        sitewide_group = (
            DBSession()
            .query(Group)
            .filter(Group.name == cfg['misc']['public_group_name'])
            .first()
        )

        obj.groups.append(sitewide_group)
        DBSession().commit()

    @staticmethod
    def teardown(user_id):
        user = DBSession().query(User).filter(User.id == user_id).first()
        if user is not None:
            # If it is, delete it
            DBSession().delete(user)
            DBSession().commit()


class AnnotationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Annotation

    data = {'unique_id': uuid.uuid4().hex}
    author = factory.SubFactory(UserFactory)
    origin = factory.LazyFunction(lambda: uuid.uuid4().hex[:10])

    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                obj.groups.append(group)
                DBSession().add(obj)
                DBSession().commit()

    @staticmethod
    def teardown(annotation):
        if is_already_deleted(annotation, Annotation):
            return

        author = annotation.author.id
        DBSession().delete(annotation)
        DBSession().commit()
        UserFactory.teardown(author)


class InstrumentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Instrument

    name = factory.LazyFunction(lambda: f'ZTF_{uuid.uuid4().hex}')
    type = 'imager'
    band = 'Optical'
    telescope = factory.SubFactory(TelescopeFactory)
    filters = ['ztfg', 'ztfr', 'ztfi']

    @staticmethod
    def teardown(instrument):
        if is_already_deleted(instrument, Instrument):
            return

        telescope = instrument.telescope.id
        DBSession().delete(instrument)
        DBSession().commit()
        TelescopeFactory.teardown(telescope)


class PhotometryFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Photometry

    instrument = factory.SubFactory(InstrumentFactory)
    mjd = factory.LazyFunction(lambda: 58000.0 + np.random.random())
    flux = factory.LazyFunction(lambda: 20 + 10 * np.random.random())
    fluxerr = factory.LazyFunction(lambda: 2 * np.random.random())
    owner_id = 1

    @staticmethod
    def teardown(photometry):
        if is_already_deleted(photometry, Photometry):
            return

        instrument = photometry.instrument
        DBSession().delete(photometry)
        DBSession().commit()
        DBSession().delete(instrument)


class ThumbnailFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Thumbnail


class SpectrumFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Spectrum

    instrument = factory.SubFactory(InstrumentFactory)
    wavelengths = np.sort(1000 * np.random.random(20))
    fluxes = 1e-9 * np.random.random(len(wavelengths))
    observed_at = datetime.datetime.now()
    owner_id = 1

    reducers = factory.LazyFunction(lambda: [UserFactory() for _ in range(2)])
    observers = factory.LazyFunction(lambda: [UserFactory() for _ in range(1)])

    @staticmethod
    def teardown(spectrum):
        if is_already_deleted(spectrum, Spectrum):
            return
        instrument = spectrum.instrument
        reducers = spectrum.reducers
        observers = spectrum.observers
        for reducer in reducers:
            UserFactory.teardown(reducer.id)
        for observer in observers:
            UserFactory.teardown(observer.id)
        DBSession().delete(spectrum)
        DBSession().commit()
        InstrumentFactory.teardown(instrument)


class StreamFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Stream

    name = factory.LazyFunction(lambda: uuid.uuid4().hex)
    users = []
    groups = []
    filters = []

    @staticmethod
    def teardown(stream_id):
        # Fetch fresh instance of stream
        stream = DBSession().query(Stream).filter(Stream.id == stream_id).first()
        if stream is not None:
            # If it is, delete it
            DBSession().delete(stream)
            DBSession().commit()


class GroupFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Group

    name = factory.LazyFunction(lambda: uuid.uuid4().hex[:15])
    users = []
    streams = []
    filters = []
    private = False

    @factory.post_generation
    def streams(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for stream in extracted:
                obj.streams.append(stream)
                DBSession().add(obj)
                DBSession().commit()

    @staticmethod
    def teardown(group_id):
        group = DBSession().query(Group).filter(Group.id == group_id).first()
        if group is not None:
            # If it is, delete it
            DBSession().delete(group)
            DBSession().commit()


class FilterFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Filter

    name = str(uuid.uuid4())

    @staticmethod
    def teardown(filter_id):
        filter_ = DBSession().query(Filter).filter(Filter.id == filter_id).first()
        if filter_ is not None:
            # If it is, delete it
            DBSession().delete(filter_)
            DBSession().commit()


class CommentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Comment

    text = f'Test comment {uuid.uuid4().hex}'

    author = factory.SubFactory(UserFactory)

    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for group in extracted:
                obj.groups.append(group)
                DBSession().add(obj)
                DBSession().commit()

    @staticmethod
    def teardown(comment):
        if is_already_deleted(comment, Comment):
            return

        author = comment.author.id
        DBSession().delete(comment)
        DBSession().commit()
        UserFactory.teardown(author)


class ObjFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Obj

    id = factory.LazyFunction(lambda: uuid.uuid4().hex)
    ra = 0.0
    dec = 0.0
    redshift = 0.0
    altdata = {"simbad": {"class": "RRLyr"}}
    origin = factory.LazyFunction(lambda: uuid.uuid4().hex)
    alias = factory.LazyFunction(lambda: uuid.uuid4().hex)

    @factory.post_generation
    def groups(obj, create, passed_groups, *args, **kwargs):
        if not passed_groups:
            passed_groups = []
        instruments = [InstrumentFactory(), InstrumentFactory()]
        # Save the generated instruments so they can be cleaned up later
        obj.instruments = instruments
        filters = ['ztfg', 'ztfr', 'ztfi']
        for instrument, filter in islice(zip(cycle(instruments), cycle(filters)), 10):
            np.random.seed()
            phot1 = PhotometryFactory(
                obj_id=obj.id,
                instrument=instrument,
                filter=filter,
                groups=passed_groups,
                origin=uuid.uuid4(),
            )
            DBSession().add(phot1)
            DBSession().add(
                PhotometryFactory(
                    obj_id=obj.id,
                    flux=99.0,
                    fluxerr=99.0,
                    instrument=instrument,
                    filter=filter,
                    groups=passed_groups,
                    origin=uuid.uuid4(),
                )
            )

            DBSession().add(ThumbnailFactory(obj_id=obj.id, type="new"))
            DBSession().add(ThumbnailFactory(obj_id=obj.id, type="ps1"))
            DBSession().add(CommentFactory(obj_id=obj.id, groups=passed_groups))
        DBSession().add(
            SpectrumFactory(
                obj_id=obj.id, instrument=instruments[0], groups=passed_groups
            )
        )
        DBSession().commit()

    @staticmethod
    def teardown(obj):
        if is_already_deleted(obj, Obj):
            return

        instruments = obj.instruments
        comment_authors = list(map(lambda x: x.author.id, obj.comments))
        for author in comment_authors:
            UserFactory.teardown(author)
        spectra = DBSession().query(Spectrum).filter(Spectrum.obj_id == obj.id).all()
        for spectrum in spectra:
            SpectrumFactory.teardown(spectrum)
        DBSession().delete(obj)
        DBSession().commit()
        for instrument in instruments:
            InstrumentFactory.teardown(instrument)


class ObservingRunFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = ObservingRun

    instrument = factory.SubFactory(
        InstrumentFactory,
        name=factory.LazyFunction(lambda: f'DBSP_{uuid.uuid4().hex}'),
        type='spectrograph',
        band='Optical',
        filters=[],
        telescope=factory.SubFactory(
            TelescopeFactory,
            name=factory.LazyFunction(
                lambda: f'Palomar 200-inch Telescope_{uuid.uuid4().hex}'
            ),
            nickname=factory.LazyFunction(lambda: f'P200_{uuid.uuid4().hex}'),
            robotic=False,
            skycam_link='/static/images/palomar.jpg',
        ),
    )

    group = factory.SubFactory(GroupFactory)
    pi = 'Danny Goldstein'
    observers = 'D. Goldstein, S. Dhawan'
    calendar_date = '3021-02-27'
    owner = factory.SubFactory(UserFactory)

    @staticmethod
    def teardown(run):
        if is_already_deleted(run, ObservingRun):
            return

        owner = run.owner.id
        instrument = run.instrument
        group = run.group.id
        DBSession().delete(run)
        DBSession().commit()
        UserFactory.teardown(owner)
        GroupFactory.teardown(group)
        InstrumentFactory.teardown(instrument)


class ClassicalAssignmentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = ClassicalAssignment

    obj = factory.SubFactory(ObjFactory)
    run = factory.SubFactory(ObservingRunFactory)
    requester = factory.SubFactory(UserFactory)
    last_modified_by = factory.SubFactory(UserFactory)
    priority = factory.LazyFunction(lambda: str(random.choice(range(1, 6))))

    @staticmethod
    def teardown(assignment):
        if is_already_deleted(assignment, ClassicalAssignment):
            return

        requester = assignment.requester.id
        run = assignment.run
        obj = assignment.obj
        last_modified_by = assignment.last_modified_by.id

        DBSession().delete(assignment)
        DBSession().commit()
        ObservingRunFactory.teardown(run)
        ObjFactory.teardown(obj)
        UserFactory.teardown(last_modified_by)
        UserFactory.teardown(requester)


class TaxonomyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Taxonomy

    name = factory.LazyFunction(lambda: uuid.uuid4().hex[:10])
    hierarchy = tdtax.taxonomy
    provenance = f"tdtax_{tdtax.__version__}"
    version = tdtax.__version__
    isLatest = True

    @factory.post_generation
    def groups(obj, create, passed_groups, *args, **kwargs):
        if not passed_groups:
            passed_groups = []

        obj.groups = passed_groups
        DBSession().add(obj)
        DBSession().commit()

    @staticmethod
    def teardown(taxonomy_id):
        taxonomy = (
            DBSession().query(Taxonomy).filter(Taxonomy.id == taxonomy_id).first()
        )
        if taxonomy is not None:
            DBSession().delete(taxonomy)
            DBSession().commit()


class ClassificationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Classification

    taxonomy = factory.SubFactory(TaxonomyFactory)
    classification = factory.LazyFunction(lambda: uuid.uuid4().hex[:10])
    author = factory.SubFactory(UserFactory)
    author_name = factory.LazyFunction(lambda: uuid.uuid4().hex[:10])
    obj = factory.SubFactory(ObjFactory)
    probability = factory.LazyFunction(lambda: float(np.random.uniform()))

    @factory.post_generation
    def groups(obj, create, passed_groups, *args, **kwargs):
        if not passed_groups:
            passed_groups = []

        obj.groups = passed_groups
        DBSession().add(obj)
        DBSession().commit()

    @staticmethod
    def teardown(classification):
        if is_already_deleted(classification, Classification):
            return

        author = classification.author.id
        obj = classification.obj
        taxonomy = classification.taxonomy.id

        DBSession().delete(classification)
        DBSession().commit()

        UserFactory.teardown(author)
        ObjFactory.teardown(obj)
        TaxonomyFactory.teardown(taxonomy)


class AllocationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Allocation

    instrument = factory.SubFactory(InstrumentFactory)
    group = (factory.SubFactory(GroupFactory),)
    pi = (factory.LazyFunction(lambda: uuid.uuid4().hex),)
    proposal_id = factory.LazyFunction(lambda: uuid.uuid4().hex)
    hours_allocated = 100

    @staticmethod
    def teardown(allocation):
        if is_already_deleted(allocation, Allocation):
            return

        instrument = allocation.instrument
        group = allocation.group.id

        DBSession().delete(allocation)
        DBSession().commit()

        InstrumentFactory.teardown(instrument)
        GroupFactory.teardown(group)


class FollowupRequestFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = FollowupRequest

    obj = (factory.SubFactory(ObjFactory),)
    allocation = (factory.SubFactory(AllocationFactory),)
    payload = (
        {
            'priority': "5",
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
        },
    )
    requester = factory.SubFactory(UserFactory)
    last_modified_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def target_groups(obj, create, passed_groups, *args, **kwargs):
        if not passed_groups:
            passed_groups = []
        obj.target_groups = passed_groups
        DBSession().add(obj)
        DBSession().commit()

    @staticmethod
    def teardown(request):
        if is_already_deleted(request, FollowupRequest):
            return

        requester = request.requester.id
        allocation = request.allocation
        obj = request.obj

        DBSession().delete(request)
        DBSession().commit()
        UserFactory.teardown(request.last_modified_by.id)
        UserFactory.teardown(requester)
        AllocationFactory.teardown(allocation)
        ObjFactory.teardown(obj)


class InvitationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Invitation

    token = factory.LazyFunction(lambda: uuid.uuid4().hex)
    admin_for_groups = []
    user_email = 'user@email.com'
    invited_by = factory.SubFactory(UserFactory)
    used = False

    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                obj.groups.append(group)
                DBSession().add(obj)
                DBSession().commit()

    @factory.post_generation
    def streams(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for stream in extracted:
                obj.streams.append(stream)
                DBSession().add(obj)
                DBSession().commit()

    @staticmethod
    def teardown(invitation):
        if is_already_deleted(invitation, Invitation):
            return

        invited_by = invitation.invited_by.id

        DBSession().delete(invitation)
        DBSession().commit()

        UserFactory.teardown(invited_by)


class NotificationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = SourceNotification

    sent_by = factory.SubFactory(UserFactory)
    source = factory.SubFactory(ObjFactory)
    additional_notes = 'abcd'
    level = 'hard'

    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                obj.groups.append(group)
                DBSession().add(obj)
                DBSession().commit()

    @staticmethod
    def teardown(notification):
        if is_already_deleted(notification, SourceNotification):
            return

        source = notification.source
        sent_by = notification.sent_by.id

        DBSession().delete(notification)
        DBSession().commit()

        ObjFactory.teardown(source)
        UserFactory.teardown(sent_by)


class UserNotificationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = UserNotification

    user = factory.SubFactory(UserFactory)
    text = 'abcd1234'
    viewed = False

    @staticmethod
    def teardown(notification):
        if is_already_deleted(notification, UserNotification):
            return

        user = notification.user.id

        DBSession().delete(notification)
        DBSession().commit()

        UserFactory.teardown(user)
