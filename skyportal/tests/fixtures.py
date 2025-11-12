import datetime
import json
import os
import pathlib
import random
import uuid
from itertools import cycle, islice
from tempfile import mkdtemp

import factory
import numpy as np
import pandas as pd
import sqlalchemy as sa
import tdtax
from sqlalchemy import inspect
from sqlalchemy.orm.exc import ObjectDeletedError

from baselayer.app.config import load_config
from baselayer.app.env import load_env
from skyportal.models import (
    Allocation,
    Annotation,
    ClassicalAssignment,
    Classification,
    Comment,
    CommentOnGCN,
    CommentOnSpectrum,
    DBSession,
    Filter,
    FollowupRequest,
    GcnEvent,
    GcnNotice,
    GcnProperty,
    GcnTag,
    Group,
    Instrument,
    Invitation,
    Localization,
    LocalizationProperty,
    LocalizationTag,
    LocalizationTile,
    Obj,
    ObservingRun,
    Photometry,
    SourceNotification,
    Spectrum,
    Stream,
    Taxonomy,
    Telescope,
    Thumbnail,
    User,
    UserNotification,
    init_db,
)
from skyportal.tests.test_util import set_server_url

TMP_DIR = mkdtemp()
env, cfg = load_env()

print("Loading test configuration from _test_config.yaml")
basedir = pathlib.Path(os.path.dirname(__file__))
cfg = load_config([(basedir / "../../test_config.yaml").absolute()])
set_server_url(f"http://localhost:{cfg['ports.app']}")
print("Setting test database to:", cfg["database"])
init_db(**cfg["database"])


def load_localization_data(path):
    """
    Load localization data from a Parquet file (uniq, probdensity, contour). Used for testing.

    Parameters
    ----------
    path : str
        Path to the CSV file containing localization data.

    Returns
    -------
    tuple
        Tuple containing the uniq, probdensity, and contour data.
    """
    df = pd.read_parquet(os.path.join(os.path.dirname(__file__), path))

    uniq = df["uniq"].values[0]
    probdensity = df["probdensity"].values[0]
    contour = df["contour"].values[0]

    # Convert string representations of lists to actual lists and dicts
    uniq = np.array([int(x) for x in uniq[1:-1].split(",")]).tolist()
    probdensity = np.array([float(x) for x in probdensity[1:-1].split(",")]).tolist()
    contour = json.loads(contour)

    return uniq, probdensity, contour


def load_localization_tiles_data(path):
    """
    Load localization tile data from a CSV file. Used for testing.

    Parameters
    ----------
    path : str
        Path to the Parquet file containing localization tile data.

    Returns
    -------
    tuple
        Tuple containing the probdensities and healpix ranges.
    """
    df = pd.read_parquet(os.path.join(os.path.dirname(__file__), path))

    return df["probdensity"].values, df["healpix"].values


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
                DBSession()
                .execute(sa.select(table).filter(table.id == instance.id))
                .scalars()
                .first()
                is None
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
    sqlalchemy_session_persistence = "commit"


class TelescopeFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Telescope

    name = factory.LazyFunction(lambda: f"Palomar 48 inch_{uuid.uuid4().hex}")
    nickname = factory.LazyFunction(lambda: f"P48_{uuid.uuid4().hex}")
    lat = 33.3563
    lon = -116.8650
    elevation = 1712.0
    diameter = 1.2
    robotic = True

    @staticmethod
    def teardown(telescope_id):
        telescope = (
            DBSession()
            .execute(sa.select(Telescope).filter(Telescope.id == telescope_id))
            .scalars()
            .first()
        )
        if telescope is not None:
            DBSession().delete(telescope)
            DBSession().commit()


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = User

    username = factory.LazyFunction(lambda: uuid.uuid4().hex)
    contact_email = factory.LazyFunction(lambda: f"{uuid.uuid4().hex[:10]}@gmail.com")
    first_name = factory.LazyFunction(lambda: f"{uuid.uuid4().hex[:4]}")
    last_name = factory.LazyFunction(lambda: f"{uuid.uuid4().hex[:4]}")

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
    def acls(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for acl in extracted:
                obj.acls.append(acl)
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
            .execute(
                sa.select(Group).filter(Group.name == cfg["misc"]["public_group_name"])
            )
            .scalars()
            .first()
        )

        obj.groups.append(sitewide_group)
        DBSession().commit()

    @staticmethod
    def teardown(user_id):
        user = (
            DBSession()
            .execute(sa.select(User).filter(User.id == user_id))
            .scalars()
            .first()
        )
        if user is not None:
            # If it is, delete it
            DBSession().refresh(user)
            DBSession().delete(user)
            DBSession().commit()


class AnnotationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Annotation

    data = {"unique_id": uuid.uuid4().hex}
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

    name = factory.LazyFunction(lambda: f"ZTF_{uuid.uuid4().hex}")
    type = "imager"
    band = "Optical"
    telescope = factory.SubFactory(TelescopeFactory)
    filters = ["ztfg", "ztfr", "ztfi"]

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
        stream = (
            DBSession()
            .execute(sa.select(Stream).filter(Stream.id == stream_id))
            .scalars()
            .first()
        )
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
    def streams(obj, create, extracted, **kwargs):  # noqa F811
        if not create:
            return
        if extracted:
            for stream in extracted:
                obj.streams.append(stream)
                DBSession().add(obj)
                DBSession().commit()

    @staticmethod
    def teardown(group_id):
        group = (
            DBSession()
            .execute(sa.select(Group).filter(Group.id == group_id))
            .scalars()
            .first()
        )
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
        filter_ = (
            DBSession()
            .execute(sa.select(Filter).filter(Filter.id == filter_id))
            .scalars()
            .first()
        )
        if filter_ is not None:
            # If it is, delete it
            DBSession().delete(filter_)
            DBSession().commit()


class CommentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Comment

    text = f"Test comment {uuid.uuid4().hex}"

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


class CommentOnSpectrumFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = CommentOnSpectrum

    text = f"Test comment {uuid.uuid4().hex}"

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
        if is_already_deleted(comment, CommentOnSpectrum):
            return

        author = comment.author.id
        DBSession().delete(comment)
        DBSession().commit()
        UserFactory.teardown(author)


class CommentOnGCNFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = CommentOnGCN

    text = f"Test GCN comment {uuid.uuid4().hex}"

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
        if is_already_deleted(comment, CommentOnGCN):
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
        filters = ["ztfg", "ztfr", "ztfi"]
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
        comment_authors = [x.author.id for x in obj.comments]
        for author in comment_authors:
            UserFactory.teardown(author)
        spectra = (
            DBSession()
            .execute(sa.select(Spectrum).filter(Spectrum.obj_id == obj.id))
            .scalars()
            .all()
        )
        for spectrum in spectra:
            SpectrumFactory.teardown(spectrum)
        DBSession().delete(obj)
        DBSession().commit()
        for instrument in instruments:
            InstrumentFactory.teardown(instrument)


class GcnNoticeFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = GcnNotice

    sent_by = factory.SubFactory(UserFactory)
    ivorn = factory.LazyFunction(lambda: f"ivo://gwnet/LVC/{uuid.uuid4().hex}")
    notice_type = "test"
    notice_format = "voevent"
    stream = factory.LazyFunction(lambda: uuid.uuid4().hex)
    date = datetime.datetime.now()
    dateobs = datetime.datetime.now()
    content = factory.LazyFunction(lambda: bytes(1024))
    has_localization = False
    localization_ingested = False

    @staticmethod
    def teardown(gcn):
        if is_already_deleted(gcn, GcnNotice):
            return

        DBSession().delete(gcn)
        DBSession().commit()


class GcnPropertyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = GcnProperty

    sent_by = factory.SubFactory(UserFactory)
    dateobs = datetime.datetime.now()
    data = {"test": 1}

    @staticmethod
    def teardown(gcn):
        if is_already_deleted(gcn, GcnProperty):
            return

        DBSession().delete(gcn)
        DBSession().commit()


class GcnTagFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = GcnTag

    sent_by = factory.SubFactory(UserFactory)
    dateobs = datetime.datetime.now()
    text = "TestTag"

    @staticmethod
    def teardown(gcn):
        if is_already_deleted(gcn, GcnTag):
            return

        DBSession().delete(gcn)
        DBSession().commit()


class LocalizationPropertyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = LocalizationProperty

    sent_by = factory.SubFactory(UserFactory)
    localization_id = 1
    data = {"test": 1}

    @staticmethod
    def teardown(localization):
        if is_already_deleted(localization, LocalizationProperty):
            return

        DBSession().delete(localization)
        DBSession().commit()


class LocalizationTagFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = LocalizationTag

    sent_by = factory.SubFactory(UserFactory)
    localization_id = 1
    text = "TestTag"

    @staticmethod
    def teardown(localization):
        if is_already_deleted(localization, LocalizationTag):
            return

        DBSession().delete(localization)
        DBSession().commit()


class LocalizationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Localization

    sent_by = factory.SubFactory(UserFactory)
    dateobs = datetime.datetime.now()
    localization_name = factory.LazyFunction(lambda: str(uuid.uuid4().hex))

    notice_id = 1
    uniq = []
    probdensity = []
    contour = {}

    @factory.post_generation
    def properties(self, create, passed_properties, **kwargs):
        if passed_properties:
            properties = LocalizationPropertyFactory(
                sent_by=self.sent_by, localization_id=self.id, data=passed_properties
            )
            DBSession().add(properties)
            self.properties = [properties]
            DBSession().commit()

    @factory.post_generation
    def tags(self, create, passed_tags, **kwargs):
        if passed_tags:
            tags = [
                LocalizationTagFactory(
                    sent_by=self.sent_by, localization_id=self.id, text=tag
                )
                for tag in passed_tags
            ]
            for tag in tags:
                DBSession().add(tag)
            self.tags = tags

            DBSession().commit()

    @factory.post_generation
    def load_localization(self, create, path=None, **kwargs):
        if path:
            uniq, probdensity, contour = load_localization_data(path)
            self.uniq = uniq
            self.probdensity = probdensity
            self.contour = contour
            DBSession().commit()

    @factory.post_generation
    def load_localization_tiles(self, create, path=None, **kwargs):
        if path:
            probdensities, healpix_ranges = load_localization_tiles_data(path)
            for i in range(len(probdensities)):
                localization_tile = LocalizationTile(
                    dateobs=self.dateobs,
                    localization_id=self.id,
                    probdensity=probdensities[i],
                    healpix=healpix_ranges[i],
                )
                DBSession().add(localization_tile)
            DBSession().commit()

    @staticmethod
    def teardown(localization):
        if is_already_deleted(localization, Localization):
            return

        DBSession().delete(localization)
        DBSession().commit()


class GcnEventFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = GcnEvent

    sent_by = factory.SubFactory(UserFactory)
    dateobs = datetime.datetime.now()
    trigger_id = factory.LazyFunction(lambda: uuid.uuid4().hex)

    @factory.post_generation
    def aliases(self, created, passed_aliases=None, **kwargs):
        if passed_aliases:
            self.aliases = passed_aliases
            DBSession().commit()

    @factory.post_generation
    def tach_id(self, created, passed_tach_id=None, **kwargs):
        if passed_tach_id:
            self.tach_id = passed_tach_id
            DBSession().commit()

    @factory.post_generation
    def gcn_notices(self, create, passed_notices=[], **kwargs):
        if passed_notices and len(passed_notices) > 0:
            new_notices = []
            for notice_dict in passed_notices:
                new_notice = GcnNoticeFactory(
                    dateobs=self.dateobs,
                    sent_by=self.sent_by,
                    ivorn=notice_dict.get("ivorn", f"ivo://test/{uuid.uuid4().hex}"),
                    notice_type=notice_dict.get("notice_type", "Test"),
                    notice_format=notice_dict.get("notice_format", "voevent"),
                    stream=notice_dict.get("stream", str(uuid.uuid4().hex)),
                    date=notice_dict.get("date", datetime.datetime.now()),
                    content=notice_dict.get("content", bytes(1024)),
                    has_localization=notice_dict.get("has_localization", False),
                    localization_ingested=notice_dict.get(
                        "localization_ingested", False
                    ),
                )
                new_notices.append(new_notice)

            for gcn_notice in new_notices:
                DBSession().add(gcn_notice)
            self.gcn_notices = new_notices
            DBSession().commit()

    @factory.post_generation
    def properties(self, create, passed_properties=None, **kwargs):
        if isinstance(passed_properties, dict) and len(passed_properties) > 0:
            properties = GcnPropertyFactory(
                dateobs=self.dateobs, sent_by=self.sent_by, data=passed_properties
            )
            DBSession().add(properties)
            self.properties = [properties]

        DBSession().commit()

    @factory.post_generation
    def localizations(self, create, passed_localizations=[], **kwargs):
        if len(passed_localizations) > 0:
            new_localizations = []
            for localization_dict in passed_localizations:
                new_loc = LocalizationFactory(
                    dateobs=self.dateobs,
                    sent_by=self.sent_by,
                    notice_id=self.gcn_notices[0].id,
                    properties=localization_dict.get("properties"),
                    tags=localization_dict.get("tags"),
                    localization_name=localization_dict.get(
                        "localization_name", f"Localization {uuid.uuid4().hex}"
                    ),
                    load_localization=localization_dict.get("localization_data_path"),
                    load_localization_tiles=localization_dict.get(
                        "localization_tiles_data_path"
                    ),
                )
                new_localizations.append(new_loc)

            for localization in new_localizations:
                DBSession().add(localization)
            self.localizations = new_localizations
            DBSession().commit()

    @staticmethod
    def teardown(gcn):
        if is_already_deleted(gcn, GcnEvent):
            return

        for notice in gcn.gcn_notices:
            GcnNoticeFactory.teardown(notice)

        for prop in gcn.properties:
            GcnPropertyFactory.teardown(prop)

        for loc in gcn.localizations:
            LocalizationFactory.teardown(loc)

        DBSession().delete(gcn)
        DBSession().commit()


class ObservingRunFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = ObservingRun

    instrument = factory.SubFactory(
        InstrumentFactory,
        name=factory.LazyFunction(lambda: f"DBSP_{uuid.uuid4().hex}"),
        type="spectrograph",
        band="Optical",
        filters=[],
        telescope=factory.SubFactory(
            TelescopeFactory,
            name=factory.LazyFunction(
                lambda: f"Palomar 200-inch Telescope_{uuid.uuid4().hex}"
            ),
            nickname=factory.LazyFunction(lambda: f"P200_{uuid.uuid4().hex}"),
            robotic=False,
            skycam_link="/static/images/palomar.jpg",
        ),
    )

    group = factory.SubFactory(GroupFactory)
    pi = "Danny Goldstein"
    observers = "D. Goldstein, S. Dhawan"
    calendar_date = "3021-02-27"
    run_end_utc = "3021-02-27 14:20:24.972000"
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
            DBSession()
            .execute(sa.select(Taxonomy).filter(Taxonomy.id == taxonomy_id))
            .scalars()
            .first()
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
            "priority": "5",
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
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
    user_email = "user@email.com"
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
    additional_notes = "abcd"
    level = "hard"

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
    text = "abcd1234"
    viewed = False

    @staticmethod
    def teardown(notification):
        if is_already_deleted(notification, UserNotification):
            return

        user = notification.user.id

        DBSession().delete(notification)
        DBSession().commit()

        UserFactory.teardown(user)
