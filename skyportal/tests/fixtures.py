import datetime
from itertools import cycle, islice
import uuid
import numpy as np
from skyportal.models import (DBSession, User, Source, Group, GroupUser,
                              GroupSource, Photometry, Spectrum, Instrument,
                              Telescope, Comment, Thumbnail)
from tempfile import mkdtemp

import factory


TMP_DIR = mkdtemp()


class BaseMeta:
    sqlalchemy_session = DBSession()
    sqlalchemy_session_persistence = 'commit'


class TelescopeFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Telescope

    name = 'Test telescope'
    nickname = 'test_scope'
    lat = 0.0
    lon = 0.0
    elevation = 0.0
    diameter = 1.0


class CommentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Comment

    text = f'Test comment {str(uuid.uuid4())}'
    ctype = 'text'
    author = 'test factory'


class InstrumentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Instrument

    name = 'Test instrument'
    type = 'Type 1'
    band = 'Band 1'
    telescope = factory.SubFactory(TelescopeFactory)


class PhotometryFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Photometry

    instrument = factory.SubFactory(InstrumentFactory)
    observed_at = factory.LazyFunction(lambda: datetime.datetime.now() -
                                    datetime.timedelta(days=np.random.randint(0, 10)))
    mag = factory.LazyFunction(lambda: 20 + 10 * np.random.random())
    e_mag = factory.LazyFunction(lambda: 2 * np.random.random())
    lim_mag = 99.


class ThumbnailFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Thumbnail

    type = 'new'


class SpectrumFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Spectrum

    instrument = factory.SubFactory(InstrumentFactory)
    wavelengths = np.sort(1000 * np.random.random(10))
    fluxes = 1e-9 * np.random.random(len(wavelengths))
    observed_at = datetime.datetime.now()


class GroupFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Group
    name = factory.LazyFunction(lambda: str(uuid.uuid4()))
    users = []


class SourceFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Source
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    ra = 0.0
    dec = 0.0
    redshift = 0.0
    simbad_class = 'RRLyr'

    @factory.post_generation
    def add_phot_spec(source, create, value, *args, **kwargs):
        instruments = [InstrumentFactory(), InstrumentFactory()]
        filters = ['g', 'rpr', 'ipr']
        for instrument, filter in islice(zip(cycle(instruments), cycle(filters)), 10):
            phot1 = PhotometryFactory(source_id=source.id,
                                      instrument=instrument,
                                      filter=filter)
            DBSession().add(phot1)
            DBSession().add(PhotometryFactory(source_id=source.id, mag=99.,
                                              e_mag=99., lim_mag=30.,
                                              instrument=instrument,
                                              filter=filter))
            DBSession().add(ThumbnailFactory(photometry=phot1))
            DBSession().add(CommentFactory(source_id=source.id))
        DBSession().add(SpectrumFactory(source_id=source.id,
                                        instrument=instruments[0]))
        DBSession().commit()


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = User

    username = factory.LazyFunction(lambda: f'{uuid.uuid4()}@cesium-ml.org')

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
