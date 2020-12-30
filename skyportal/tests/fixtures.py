import datetime
import os
import pathlib
import random
import uuid
from itertools import cycle, islice
from tempfile import mkdtemp

import factory
import numpy as np

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


class BaseMeta:
    sqlalchemy_session = DBSession()
    sqlalchemy_session_persistence = 'commit'


class TelescopeFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Telescope

    name = factory.LazyFunction(lambda: f'Palomar 48 inch_{str(uuid.uuid4())}')
    nickname = factory.LazyFunction(lambda: f'P48_{str(uuid.uuid4())}')
    lat = 33.3563
    lon = -116.8650
    elevation = 1712.0
    diameter = 1.2
    robotic = True


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = User

    username = factory.LazyFunction(lambda: str(uuid.uuid4()))
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


class AnnotationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Annotation

    data = {'unique_id': str(uuid.uuid4())}
    author = factory.SubFactory(UserFactory)
    origin = factory.LazyFunction(lambda: str(uuid.uuid4())[:10])

    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                obj.groups.append(group)
                DBSession().add(obj)
                DBSession().commit()


class InstrumentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Instrument

    name = factory.LazyFunction(lambda: f'ZTF_{str(uuid.uuid4())}')
    type = 'imager'
    band = 'Optical'
    telescope = factory.SubFactory(TelescopeFactory)
    filters = ['ztfg', 'ztfr', 'ztfi']


class PhotometryFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Photometry

    instrument = factory.SubFactory(InstrumentFactory)
    mjd = factory.LazyFunction(lambda: 58000.0 + np.random.random())
    flux = factory.LazyFunction(lambda: 20 + 10 * np.random.random())
    fluxerr = factory.LazyFunction(lambda: 2 * np.random.random())
    owner_id = 1


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


class StreamFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Stream

    name = factory.LazyFunction(lambda: str(uuid.uuid4()))
    users = []
    groups = []
    filters = []


class GroupFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Group

    name = factory.LazyFunction(lambda: str(uuid.uuid4())[:15])
    users = []
    streams = []
    filters = []
    private = False

    # @factory.post_generation
    # def streams(obj, create, extracted, **kwargs):
    #     if not create:
    #         return
    #
    #     if extracted:
    #         for stream in extracted:
    #             obj.streams.append(stream)
    #             DBSession().add(obj)
    #             DBSession().commit()


class FilterFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Filter

    name = str(uuid.uuid4())


class CommentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Comment

    text = f'Test comment {str(uuid.uuid4())}'
    ctype = 'text'
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


class ObjFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Obj

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    ra = 0.0
    dec = 0.0
    redshift = 0.0
    altdata = {"simbad": {"class": "RRLyr"}}

    @factory.post_generation
    def groups(obj, create, passed_groups, *args, **kwargs):
        if not passed_groups:
            passed_groups = []
        instruments = [InstrumentFactory(), InstrumentFactory()]
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


class ObservingRunFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = ObservingRun

    instrument = factory.SubFactory(
        InstrumentFactory,
        name=factory.LazyFunction(lambda: f'DBSP_{uuid.uuid4()}'),
        type='spectrograph',
        band='Optical',
        filters=[],
        telescope=factory.SubFactory(
            TelescopeFactory,
            name=factory.LazyFunction(
                lambda: f'Palomar 200-inch Telescope_{uuid.uuid4()}'
            ),
            nickname=factory.LazyFunction(lambda: f'P200_{uuid.uuid4()}'),
            robotic=False,
            skycam_link='/static/images/palomar.jpg',
        ),
    )

    group = factory.SubFactory(GroupFactory)
    pi = 'Danny Goldstein'
    observers = 'D. Goldstein, S. Dhawan'
    calendar_date = '3021-02-27'
    owner = factory.SubFactory(UserFactory)


class ClassicalAssignmentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = ClassicalAssignment

    obj = factory.SubFactory(ObjFactory)
    run = factory.SubFactory(ObservingRunFactory)
    requester = factory.SubFactory(UserFactory)
    last_modified_by = factory.SubFactory(UserFactory)
    priority = factory.LazyFunction(lambda: str(random.choice(range(1, 6))))


class TaxonomyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Taxonomy

    name = factory.LazyFunction(lambda: str(uuid.uuid4())[:10])
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


class ClassificationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Classification

    taxonomy = factory.SubFactory(TaxonomyFactory)
    classification = factory.LazyFunction(lambda: str(uuid.uuid4())[:10])
    author = factory.SubFactory(UserFactory)
    author_name = factory.LazyFunction(lambda: str(uuid.uuid4())[:10])
    obj = factory.SubFactory(ObjFactory)
    probability = factory.LazyFunction(lambda: float(np.random.uniform()))

    @factory.post_generation
    def groups(obj, create, passed_groups, *args, **kwargs):
        if not passed_groups:
            passed_groups = []

        obj.groups = passed_groups
        DBSession().add(obj)
        DBSession().commit()


class AllocationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Allocation

    instrument = factory.SubFactory(InstrumentFactory)
    group = (factory.SubFactory(GroupFactory),)
    pi = (factory.LazyFunction(lambda: str(uuid.uuid4())),)
    proposal_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    hours_allocated = 100


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
