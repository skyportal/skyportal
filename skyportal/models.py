import arrow
import uuid
import re
from datetime import datetime, timezone
from astropy import units as u
from astropy import table
import astroplan
import numpy as np
import sqlalchemy as sa
from sqlalchemy import cast
from sqlalchemy.orm.session import object_session
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import relationship
from sqlalchemy.orm import deferred
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils import ArrowType, URLType
import gcn
import enum

from astropy import coordinates as ap_coord
import healpy as hp
import healpix_alchemy as ha
from ligo.skymap.bayestar import rasterize

from baselayer.app.models import (init_db, join_model, Base, DBSession, ACL,
                                  Role, User, Token)
from baselayer.app.custom_exceptions import AccessError

import astroplan
import timezonefinder
from astropy import units as u
from astropy import time as ap_time

from . import schema
from .enum_types import (allowed_bandpasses, thumbnail_types, instrument_types,
                         followup_priorities)


# In the AB system, a brightness of 23.9 mag corresponds to 1 microJy.
# All DB fluxes are stored in microJy (AB).
PHOT_ZP = 23.9
PHOT_SYS = 'ab'


def is_owned_by(self, user_or_token):
    """Generic ownership logic for any `skyportal` ORM model.

    Models with complicated ownership logic should implement their own method
    instead of adding too many additional conditions here.
    """
    if hasattr(self, 'tokens'):
        return user_or_token in self.tokens
    if hasattr(self, 'groups'):
        return bool(set(self.groups) & set(user_or_token.accessible_groups))
    if hasattr(self, 'group'):
        return self.group in user_or_token.accessible_groups
    if hasattr(self, 'users'):
        if hasattr(user_or_token, 'created_by'):
            if user_or_token.created_by in self.users:
                return True
        return user_or_token in self.users

    raise NotImplementedError(f"{type(self).__name__} object has no owner")


Base.is_owned_by = is_owned_by


class NumpyArray(sa.types.TypeDecorator):
    impl = psql.ARRAY(sa.Float)

    def process_result_value(self, value, dialect):
        return np.array(value)


class Group(Base):
    name = sa.Column(sa.String, unique=True, nullable=False)

    streams = relationship('Stream', secondary='stream_groups',
                           back_populates='groups',
                           passive_deletes=True)
    users = relationship('User', secondary='group_users',
                         back_populates='groups',
                         passive_deletes=True)
    group_users = relationship('GroupUser', back_populates='group',
                               cascade='save-update, merge, refresh-expire, expunge',
                               passive_deletes=True)

    filter = relationship("Filter", uselist=False, back_populates="group")
    observing_runs = relationship('ObservingRun', back_populates='group')
    photometry = relationship("Photometry", secondary="group_photometry",
                              back_populates="groups",
                              cascade="save-update, merge, refresh-expire, expunge",
                              passive_deletes=True)
    spectra = relationship("Spectrum", secondary="group_spectra",
                           back_populates="groups",
                           cascade="save-update, merge, refresh-expire, expunge",
                           passive_deletes=True)
    single_user_group = sa.Column(sa.Boolean, default=False)


GroupUser = join_model('group_users', Group, User)
GroupUser.admin = sa.Column(sa.Boolean, nullable=False, default=False)


class Stream(Base):
    name = sa.Column(sa.String, unique=True, nullable=False)
    url = sa.Column(sa.String, unique=True, nullable=False)
    username = sa.Column(sa.String)
    password = sa.Column(sa.String)

    groups = relationship('Group', secondary='stream_groups',
                          back_populates='streams',
                          passive_deletes=True)


StreamGroup = join_model('stream_groups', Stream, Group)


User.groups = relationship('Group', secondary='group_users',
                           back_populates='users',
                           passive_deletes=True)


@property
def user_or_token_accessible_groups(self):
    if "System admin" in [acl.id for acl in self.acls]:
        return Group.query.all()
    return self.groups


User.accessible_groups = user_or_token_accessible_groups
Token.accessible_groups = user_or_token_accessible_groups


@property
def token_groups(self):
    return self.created_by.groups


Token.groups = token_groups


class Obj(Base, ha.Point):
    id = sa.Column(sa.String, primary_key=True)
    # TODO should this column type be decimal? fixed-precison numeric

    ra_dis = sa.Column(sa.Float)
    dec_dis = sa.Column(sa.Float)

    ra_err = sa.Column(sa.Float, nullable=True)
    dec_err = sa.Column(sa.Float, nullable=True)

    offset = sa.Column(sa.Float, default=0.0)
    redshift = sa.Column(sa.Float, nullable=True)

    # Contains all external metadata, e.g. simbad, pan-starrs, tns, gaia
    altdata = sa.Column(JSONB, nullable=True,
                        doc="Misc. alternative metadata stored in JSON format, e.g. "
                        "`{'gaia': {'info': {'Teff': 5780}}}`")

    dist_nearest_source = sa.Column(sa.Float, nullable=True)
    mag_nearest_source = sa.Column(sa.Float, nullable=True)
    e_mag_nearest_source = sa.Column(sa.Float, nullable=True)

    transient = sa.Column(sa.Boolean, default=False)
    varstar = sa.Column(sa.Boolean, default=False)
    is_roid = sa.Column(sa.Boolean, default=False)

    score = sa.Column(sa.Float, nullable=True)

    origin = sa.Column(sa.String, nullable=True)

    comments = relationship('Comment', back_populates='obj',
                            cascade='save-update, merge, refresh-expire, expunge',
                            passive_deletes=True,
                            order_by="Comment.created_at")

    classifications = relationship(
        'Classification', back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        order_by="Classification.created_at")

    photometry = relationship('Photometry', back_populates='obj',
                              cascade='save-update, merge, refresh-expire, expunge',
                              single_parent=True,
                              passive_deletes=True,
                              order_by="Photometry.mjd")

    detect_photometry_count = sa.Column(sa.Integer, nullable=True)

    spectra = relationship('Spectrum', back_populates='obj',
                           cascade='save-update, merge, refresh-expire, expunge',
                           single_parent=True,
                           passive_deletes=True,
                           order_by="Spectrum.observed_at")
    thumbnails = relationship('Thumbnail', back_populates='obj',
                              secondary='photometry',
                              cascade='save-update, merge, refresh-expire, expunge',
                              passive_deletes=True)

    followup_requests = relationship('FollowupRequest', back_populates='obj')
    assignments = relationship('ClassicalAssignment', back_populates='obj')


    @hybrid_property
    def last_detected(self):
        detections = [phot.iso for phot in self.photometry if phot.snr and phot.snr > 5]
        return max(detections) if detections else None

    @last_detected.expression
    def last_detected(cls):
        return sa.select([sa.func.max(Photometry.iso)]) \
                 .where(Photometry.obj_id == cls.id) \
                 .where(Photometry.snr > 5.) \
                 .group_by(Photometry.obj_id) \
                 .label('last_detected')

    def add_linked_thumbnails(self):
        sdss_thumb = Thumbnail(photometry=self.photometry[0],
                               public_url=self.sdss_url,
                               type='sdss')
        dr8_thumb = Thumbnail(photometry=self.photometry[0],
                              public_url=self.desi_dr8_url,
                              type='dr8')
        DBSession().add_all([sdss_thumb, dr8_thumb])
        DBSession().commit()

    @property
    def sdss_url(self):
        """Construct URL for public Sloan Digital Sky Survey (SDSS) cutout."""
        return (f"http://skyserver.sdss.org/dr12/SkyserverWS/ImgCutout/getjpeg"
                f"?ra={self.ra}&dec={self.dec}&scale=0.3&width=200&height=200"
                f"&opt=G&query=&Grid=on")

    @property
    def desi_dr8_url(self):
        """Construct URL for public DESI DR8 cutout."""
        return (f"http://legacysurvey.org/viewer/jpeg-cutout?ra={self.ra}"
                f"&dec={self.dec}&size=200&layer=dr8&pixscale=0.262&bands=grz")

    @property
    def target(self):
        """Representation of this Obj as an astroplan.FixedTarget."""
        coord = ap_coord.SkyCoord(self.ra, self.dec, unit='deg')
        return astroplan.FixedTarget(name=self.id, coord=coord)

    def airmass(self, telescope, time, below_horizon=np.inf):
        """Return the airmass of the object at a given time. Uses the Pickering
        (2002) interpolation of the Rayleigh (molecular atmosphere) airmass.

        The Pickering interpolation tends toward 38.7494 as the altitude
        approaches zero.

        Parameters
        ----------
        telescope : `skyportal.models.Telescope`
            The telescope to use for the airmass calculation
        time : `astropy.time.Time` or list of astropy.time.Time`
            The time or times at which to calculate the airmass
        below_horizon : scalar, Numeric
            Airmass value to assign when an object is below the horizon.
            An object is "below the horizon" when its altitude is less than
            zero degrees.

        Returns
        -------
        airmass : ndarray
           The airmass of the Obj at the requested times
        """

        output_shape = np.shape(time)
        time = np.atleast_1d(time)
        altitude = self.altitude(telescope, time).to('degree').value
        above = altitude > 0

        # use Pickering (2002) interpolation to calculate the airmass
        # The Pickering interpolation tends toward 38.7494 as the altitude
        # approaches zero.
        sinarg = np.zeros_like(altitude)
        airmass = np.ones_like(altitude) * np.inf
        sinarg[above] = altitude[above] + 244 / (165 + 47 * altitude[above] ** 1.1)
        airmass[above] = 1. / np.sin(np.deg2rad(sinarg[above]))

        # set objects below the horizon to an airmass of infinity
        airmass[~above] = below_horizon
        airmass = airmass.reshape(output_shape)

        return airmass

    def altitude(self, telescope, time):
        """Return the altitude of the object at a given time.

        Parameters
        ----------
        telescope : `skyportal.models.Telescope`
            The telescope to use for the altitude calculation

        time : `astropy.time.Time`
            The time or times at which to calculate the altitude

        Returns
        -------
        alt : `astropy.coordinates.AltAz`
           The altitude of the Obj at the requested times
        """

        return telescope.observer.altaz(time, self.target).alt


class Filter(Base):
    query_string = sa.Column(sa.String, nullable=False, unique=False)
    group_id = sa.Column(sa.ForeignKey("groups.id"), nullable=False,
                         index=True)
    group = relationship("Group", foreign_keys=[group_id], back_populates="filter")


Candidate = join_model("candidates", Filter, Obj)
Candidate.passed_at = sa.Column(sa.DateTime, nullable=True)
Candidate.passing_alert_id = sa.Column(sa.BigInteger)


def get_candidate_if_owned_by(obj_id, user_or_token, options=[]):
    if Candidate.query.filter(Candidate.obj_id == obj_id).first() is None:
        return None
    user_group_ids = [g.id for g in user_or_token.accessible_groups]
    c = (
        Candidate.query.filter(Candidate.obj_id == obj_id)
        .filter(
            Candidate.filter_id.in_(
                DBSession.query(Filter.id).filter(Filter.group_id.in_(user_group_ids))
            )
        )
        .options(options)
        .first()
    )
    if c is None:
        raise AccessError("Insufficient permissions.")
    return c.obj


def candidate_is_owned_by(self, user_or_token):
    return self.filter.group in user_or_token.accessible_groups


Candidate.get_obj_if_owned_by = get_candidate_if_owned_by
Candidate.is_owned_by = candidate_is_owned_by


Source = join_model("sources", Group, Obj)
"""User.sources defines the logic for whether a user has access to a source;
   if this gets more complicated it should become a function/`hybrid_property`
   rather than a `relationship`.
"""
Source.saved_by_id = sa.Column(sa.ForeignKey("users.id"), nullable=True, unique=False,
                               index=True)
Source.saved_by = relationship("User", foreign_keys=[Source.saved_by_id],
                               backref="saved_sources")
Source.saved_at = sa.Column(sa.DateTime, nullable=True)
Source.active = sa.Column(sa.Boolean, server_default="true")
Source.requested = sa.Column(sa.Boolean, server_default="false")
Source.unsaved_by_id = sa.Column(sa.ForeignKey("users.id"), nullable=True, unique=False,
                                 index=True)
Source.unsaved_by = relationship("User", foreign_keys=[Source.unsaved_by_id])


def source_is_owned_by(self, user_or_token):
    source_group_ids = [row[0] for row in DBSession.query(
        Source.group_id).filter(Source.obj_id == self.obj_id).all()]
    return bool(set(source_group_ids) & {g.id for g in user_or_token.accessible_groups})


def get_source_if_owned_by(obj_id, user_or_token, options=[]):
    if Source.query.filter(Source.obj_id == obj_id).first() is None:
        return None
    user_group_ids = [g.id for g in user_or_token.accessible_groups]
    s = (Source.query.filter(Source.obj_id == obj_id)
         .filter(Source.group_id.in_(user_group_ids)).options(options).first())
    if s is None:
        raise AccessError("Insufficient permissions.")
    return s.obj


Source.is_owned_by = source_is_owned_by
Source.get_obj_if_owned_by = get_source_if_owned_by


def get_obj_if_owned_by(obj_id, user_or_token, options=[]):
    if Obj.query.get(obj_id) is None:
        return None
    try:
        obj = Source.get_obj_if_owned_by(obj_id, user_or_token, options)
    except AccessError:  # They may still be able to view the associated Candidate
        obj = Candidate.get_obj_if_owned_by(obj_id, user_or_token, options)
        if obj is None:
            # If user can't view associated Source, and there's no Candidate they can
            # view, raise AccessError
            raise
    if obj is None:  # There is no associated Source/Cand, so check based on photometry
        if Obj.get_photometry_owned_by_user(obj_id, user_or_token):
            return Obj.query.options(options).get(obj_id)
        raise AccessError("Insufficient permissions.")
    # If we get here, the user has access to either the associated Source or Candidate
    return obj


Obj.get_if_owned_by = get_obj_if_owned_by


def get_obj_comments_owned_by(self, user_or_token):
    return [comment for comment in self.comments if comment.is_owned_by(user_or_token)]


Obj.get_comments_owned_by = get_obj_comments_owned_by


def get_obj_classifications_owned_by(self, user_or_token):
    return [classifications for classifications in self.classifications if classifications.is_owned_by(user_or_token)]


Obj.get_classifications_owned_by = get_obj_classifications_owned_by


def get_photometry_owned_by_user(obj_id, user_or_token):
    return (
        Photometry.query.filter(Photometry.obj_id == obj_id)
        .filter(
            Photometry.groups.any(Group.id.in_(
                [g.id for g in user_or_token.accessible_groups]
            ))
        )
        .all()
    )


Obj.get_photometry_owned_by_user = get_photometry_owned_by_user


def get_spectra_owned_by(obj_id, user_or_token):
    return (
        Spectrum.query.filter(Spectrum.obj_id == obj_id)
        .filter(
            Spectrum.groups.any(Group.id.in_(
                [g.id for g in user_or_token.accessible_groups]
            ))
        )
        .all()
    )


Obj.get_spectra_owned_by = get_spectra_owned_by


User.sources = relationship('Obj', backref='users',
                            secondary='join(Group, sources).join(group_users)',
                            primaryjoin='group_users.c.user_id == users.c.id',
                            passive_deletes=True)


class SourceView(Base):
    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, unique=False, index=True)
    username_or_token_id = sa.Column(sa.String, nullable=False, unique=False)
    is_token = sa.Column(sa.Boolean, nullable=False, default=False)
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.now,
                           index=True)


class Telescope(Base):
    name = sa.Column(sa.String, unique=True, nullable=False)
    nickname = sa.Column(sa.String, nullable=False)
    lat = sa.Column(sa.Float, nullable=True, doc='Latitude in deg.')
    lon = sa.Column(sa.Float, nullable=True, doc='Longitude in deg.')
    elevation = sa.Column(sa.Float, nullable=True, doc='Elevation in meters.')
    diameter = sa.Column(sa.Float, nullable=False, doc='Diameter in meters.')
    skycam_link = sa.Column(URLType, nullable=True,
                            doc="Link to the telescope's sky camera.")
    robotic = sa.Column(sa.Boolean, default=False, nullable=False,
                        doc="Is this telescope robotic?")

    instruments = relationship('Instrument', back_populates='telescope',
                               cascade='save-update, merge, refresh-expire, expunge',
                               passive_deletes=True)

    @property
    def observer(self):
        tf = timezonefinder.TimezoneFinder()
        local_tz = tf.timezone_at(lng=self.lon, lat=self.lat)
        return astroplan.Observer(longitude=self.lon * u.deg,
                                  latitude=self.lat * u.deg,
                                  elevation=self.elevation * u.m,
                                  timezone=local_tz)


class ArrayOfEnum(ARRAY):
    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)

    def result_processor(self, dialect, coltype):
        super_rp = super(ArrayOfEnum, self).result_processor(dialect, coltype)

        def handle_raw_string(value):
            if value == None or value == '{}':  # 2nd case, empty array
                return []
            inner = re.match(r"^{(.*)}$", value).group(1)
            return inner.split(",")

        def process(value):
            return super_rp(handle_raw_string(value))
        return process


class Instrument(Base):
    name = sa.Column(sa.String, unique=True, nullable=False)
    type = sa.Column(instrument_types, nullable=False)

    band = sa.Column(sa.String)
    telescope_id = sa.Column(sa.ForeignKey('telescopes.id', ondelete='CASCADE'),
                             nullable=False, index=True)
    telescope = relationship('Telescope', back_populates='instruments')

    followup_requests = relationship('FollowupRequest',
                                     back_populates='instrument')

    photometry = relationship('Photometry', back_populates='instrument')
    spectra = relationship('Spectrum', back_populates='instrument')

    # can be [] if an instrument is spec only
    filters = sa.Column(ArrayOfEnum(allowed_bandpasses), nullable=False,
                        default=[], doc='List of filters on the instrument '
                                        '(if any).')

    observing_runs = relationship('ObservingRun', back_populates='instrument')

    @property
    def does_spectroscopy(self):
        return 'spec' in self.type

    @property
    def does_imaging(self):
        return 'imag' in self.type


class Taxonomy(Base):
    __tablename__ = 'taxonomies'
    name = sa.Column(sa.String, nullable=False,
                     doc='Short string to make this taxonomy memorable '
                         'to end users.'
                     )
    hierarchy = sa.Column(JSONB, nullable=False,
                          doc='Nested JSON describing the taxonomy '
                              'which should be validated against '
                              'a schema before entry'
                          )
    provenance = sa.Column(sa.String, nullable=True,
                           doc='Identifier (e.g., URL or git hash) that '
                               'uniquely ties this taxonomy back '
                               'to an origin or place of record'
                           )
    version = sa.Column(sa.String, nullable=False,
                        doc='Semantic version of this taxonomy'
                        )

    isLatest = sa.Column(sa.Boolean, default=True, nullable=False,
                         doc='Consider this the latest version of '
                             'the taxonomy with this name? Defaults '
                             'to True.'
                         )
    groups = relationship("Group", secondary="group_taxonomy",
                          cascade="save-update,"
                                  "merge, refresh-expire, expunge",
                          passive_deletes=True
                          )

    classifications = relationship(
        'Classification', back_populates='taxonomy',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        order_by="Classification.created_at")


GroupTaxonomy = join_model("group_taxonomy", Group, Taxonomy)


def get_taxonomy_usable_by_user(taxonomy_id, user_or_token):
    return (
        Taxonomy.query.filter(Taxonomy.id == taxonomy_id)
        .filter(
            Taxonomy.groups.any(Group.id.in_([g.id for g in user_or_token.groups]))
        )
        .all()
    )


Taxonomy.get_taxonomy_usable_by_user = get_taxonomy_usable_by_user


class Comment(Base):
    text = sa.Column(sa.String, nullable=False)
    ctype = sa.Column(sa.Enum('text', 'redshift',
                              name='comment_types', validate_strings=True))

    attachment_name = sa.Column(sa.String, nullable=True)
    attachment_type = sa.Column(sa.String, nullable=True)
    attachment_bytes = sa.Column(sa.types.LargeBinary, nullable=True)

    origin = sa.Column(sa.String, nullable=True)
    author = sa.Column(sa.String, nullable=False)
    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    obj = relationship('Obj', back_populates='comments')
    groups = relationship("Group", secondary="group_comments",
                          cascade="save-update, merge, refresh-expire, expunge",
                          passive_deletes=True)


GroupComment = join_model("group_comments", Group, Comment)


class Classification(Base):
    classification = sa.Column(sa.String, nullable=False)
    taxonomy_id = sa.Column(sa.ForeignKey('taxonomies.id', ondelete='CASCADE'),
                            nullable=False, index=True)
    taxonomy = relationship('Taxonomy', back_populates='classifications')
    probability = sa.Column(sa.Float,
                            doc='User-assigned probability of belonging '
                            'to this class', nullable=True)

    author_id = sa.Column(sa.ForeignKey('users.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    author = relationship('User')
    author_name = sa.Column(sa.String, nullable=False)
    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    obj = relationship('Obj', back_populates='classifications')
    groups = relationship("Group", secondary="group_classifications",
                          cascade="save-update, merge, refresh-expire, expunge",
                          passive_deletes=True)


GroupClassifications = join_model("group_classifications", Group, Classification)


class Photometry(Base, ha.Point):
    __tablename__ = 'photometry'
    mjd = sa.Column(sa.Float, nullable=False, doc='MJD of the observation.')
    flux = sa.Column(sa.Float,
                     doc='Flux of the observation in µJy. '
                         'Corresponds to an AB Zeropoint of 23.9 in all '
                         'filters.')
    fluxerr = sa.Column(sa.Float, nullable=False,
                        doc='Gaussian error on the flux in µJy.')
    filter = sa.Column(allowed_bandpasses, nullable=False,
                       doc='Filter with which the observation was taken.')

    ra_unc = sa.Column(sa.Float, doc="Uncertainty of ra position [arcsec]")
    dec_unc = sa.Column(sa.Float, doc="Uncertainty of dec position [arcsec]")

    original_user_data = sa.Column(JSONB, doc='Original data passed by the user '
                                              'through the PhotometryHandler.POST '
                                              'API or the PhotometryHandler.PUT '
                                              'API. The schema of this JSON '
                                              'validates under either '
                                              'schema.PhotometryFlux or schema.PhotometryMag '
                                              '(depending on how the data was passed).')
    altdata = sa.Column(JSONB)
    upload_id = sa.Column(sa.String, nullable=False,
                          default=lambda: str(uuid.uuid4()))
    alert_id = sa.Column(sa.BigInteger, nullable=True, unique=True)

    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    obj = relationship('Obj', back_populates='photometry')
    groups = relationship("Group", secondary="group_photometry",
                          back_populates="photometry",
                          cascade="save-update, merge, refresh-expire, expunge",
                          passive_deletes=True)
    instrument_id = sa.Column(sa.ForeignKey('instruments.id'),
                              nullable=False, index=True)
    instrument = relationship('Instrument', back_populates='photometry')
    thumbnails = relationship('Thumbnail', passive_deletes=True)

    @hybrid_property
    def mag(self):
        if self.flux is not None and self.flux > 0:
            return -2.5 * np.log10(self.flux) + PHOT_ZP
        else:
            return None

    @hybrid_property
    def e_mag(self):
        if self.flux is not None and self.flux > 0 and self.fluxerr > 0:
            return (2.5 / np.log(10)) * (self.fluxerr / self.flux)
        else:
            return None

    @mag.expression
    def mag(cls):
        return sa.case(
            [
                sa.and_(cls.flux != None, cls.flux > 0),
                -2.5 * sa.func.log(cls.flux) + PHOT_ZP,
            ],
            else_=None
        )

    @e_mag.expression
    def e_mag(cls):
        return sa.case(
            [
                (sa.and_(cls.flux != None, cls.flux > 0, cls.fluxerr > 0),
                 2.5 / sa.func.ln(10) * cls.fluxerr / cls.flux)
            ],
            else_=None
        )

    @hybrid_property
    def jd(self):
        return self.mjd + 2_400_000.5

    @hybrid_property
    def iso(self):
        return arrow.get((self.mjd - 40_587.5) * 86400.)

    @iso.expression
    def iso(cls):
        # converts MJD to unix timestamp
        local = sa.func.to_timestamp((cls.mjd - 40_587.5) * 86400.)
        return sa.func.timezone('UTC', local)

    @hybrid_property
    def snr(self):
        return self.flux / self.fluxerr if self.flux and self.fluxerr else None

    @snr.expression
    def snr(self):
        return self.flux / self.fluxerr


GroupPhotometry = join_model("group_photometry", Group, Photometry)


class Spectrum(Base):
    __tablename__ = 'spectra'
    # TODO better numpy integration
    wavelengths = sa.Column(NumpyArray, nullable=False)
    fluxes = sa.Column(NumpyArray, nullable=False)
    errors = sa.Column(NumpyArray)

    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    obj = relationship('Obj', back_populates='spectra')
    observed_at = sa.Column(sa.DateTime, nullable=False)
    origin = sa.Column(sa.String, nullable=True)
    # TODO program?
    instrument_id = sa.Column(sa.ForeignKey('instruments.id',
                                            ondelete='CASCADE'),
                              nullable=False, index=True)
    instrument = relationship('Instrument', back_populates='spectra')
    groups = relationship("Group", secondary="group_spectra",
                          back_populates="spectra",
                          cascade="save-update, merge, refresh-expire, expunge",
                          passive_deletes=True)

    @classmethod
    def from_ascii(cls, filename, obj_id, instrument_id, observed_at):
        data = np.loadtxt(filename)
        if data.shape[1] != 2:  # TODO support other formats
            raise ValueError(f"Expected 2 columns, got {data.shape[1]}")

        return cls(wavelengths=data[:, 0], fluxes=data[:, 1],
                   obj_id=obj_id, instrument_id=instrument_id,
                   observed_at=observed_at)


GroupSpectrum = join_model("group_spectra", Group, Spectrum)


# def format_public_url(context):
#    """TODO migrate this to broker tools"""
#    file_uri = context.current_parameters.get('file_uri')
#    if file_uri is None:
#        return None
#    elif file_uri.startswith('s3'):  # TODO is this reliable?
#        raise NotImplementedError
#    elif file_uri.startswith('http://'): # TODO is this reliable?
#        return file_uri
#    else:  # local file
#        return '/' + file_uri.lstrip('./')



class FollowupRequest(Base):
    requester = relationship(User, back_populates='followup_requests')
    requester_id = sa.Column(sa.ForeignKey('users.id', ondelete='CASCADE'),
                             nullable=False, index=True)
    obj = relationship('Obj', back_populates='followup_requests')
    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    instrument = relationship(Instrument, back_populates='followup_requests')
    instrument_id = sa.Column(sa.ForeignKey('instruments.id'), nullable=False,
                              index=True)
    start_date = sa.Column(ArrowType, nullable=False)
    end_date = sa.Column(ArrowType, nullable=False)
    filters = sa.Column(psql.ARRAY(sa.String), nullable=True)
    exposure_time = sa.Column(sa.String, nullable=True)
    priority = sa.Column(sa.Enum('1', '2', '3', '4', '5',
                                 name='priority'))
    editable = sa.Column(sa.Boolean, nullable=False, default=True)
    status = sa.Column(sa.String(), nullable=False, default="pending")


User.followup_requests = relationship('FollowupRequest', back_populates='requester')

class Thumbnail(Base):
    # TODO delete file after deleting row
    type = sa.Column(thumbnail_types, doc='Thumbnail type (e.g., ref, new, sub, dr8, ...)')
    file_uri = sa.Column(sa.String(), nullable=True, index=False, unique=False)
    public_url = sa.Column(sa.String(), nullable=True, index=False, unique=False)
    origin = sa.Column(sa.String, nullable=True)
    photometry_id = sa.Column(sa.ForeignKey('photometry.id', ondelete='CASCADE'),
                              nullable=False, index=True)
    photometry = relationship('Photometry', back_populates='thumbnails')
    obj = relationship('Obj', back_populates='thumbnails', uselist=False,
                       secondary='photometry',
                       passive_deletes=True)


class ObservingRun(Base):

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'), nullable=False,
        index=True
    )
    instrument = relationship(
        'Instrument', cascade='save-update, merge, refresh-expire, expunge',
        uselist=False, back_populates='observing_runs'
    )

    # name of the PI
    pi = sa.Column(sa.String)
    observers = sa.Column(sa.String)

    sources = relationship(
        'Obj', secondary='join(ClassicalAssignment, Obj)',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True
    )

    # let this be nullable to accommodate external groups' runs
    group = relationship('Group', back_populates='observing_runs')
    group_id = sa.Column(sa.ForeignKey('groups.id', ondelete='CASCADE'),
                         nullable=True, index=True)

    # the person who uploaded the run
    owner = relationship('User', back_populates='observing_runs')
    owner_id = sa.Column(sa.ForeignKey('users.id', ondelete='CASCADE'),
                         nullable=False, index=True)

    assignments = relationship('ClassicalAssignment', passive_deletes=True)
    calendar_date = sa.Column(sa.Date, nullable=False, index=True)

    @property
    def _calendar_noon(self):
        observer = self.instrument.telescope.observer
        year = self.calendar_date.year
        month = self.calendar_date.month
        day = self.calendar_date.day
        hour = 12
        noon = datetime(year=year, month=month, day=day, hour=hour,
                        tzinfo=observer.timezone)
        noon = noon.astimezone(timezone.utc).timestamp()
        noon = ap_time.Time(noon, format='unix')
        return noon

    @property
    def sunset(self):
        return self.instrument.telescope.observer.sun_set_time(
            self._calendar_noon, which='next'
        )

    @property
    def sunrise(self):
        return self.instrument.telescope.observer.sun_rise_time(
            self._calendar_noon, which='next'
        )

    @property
    def twilight_evening_nautical(self):
        return self.instrument.telescope.observer.twilight_evening_nautical(
            self._calendar_noon, which='next'
        )

    @property
    def twilight_morning_nautical(self):
        return self.instrument.telescope.observer.twilight_morning_nautical(
            self._calendar_noon, which='next'
        )

    @property
    def twilight_evening_astronomical(self):
        return self.instrument.telescope.observer.twilight_evening_astronomical(
            self._calendar_noon, which='next'
        )

    @property
    def twilight_morning_astronomical(self):
        return self.instrument.telescope.observer.twilight_morning_astronomical(
            self._calendar_noon, which='next'
        )


User.observing_runs = relationship(
    'ObservingRun', cascade='save-update, merge, refresh-expire, expunge'
)


class ClassicalAssignment(Base):

    requester = relationship('User', back_populates='assignments')
    requester_id = sa.Column(sa.ForeignKey('users.id', ondelete='CASCADE'),
                             nullable=False, index=True)

    obj = relationship('Obj', back_populates='assignments')
    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, index=True)

    comment = sa.Column(sa.String())
    status = sa.Column(sa.String(), nullable=False, default="pending")
    priority = sa.Column(followup_priorities, nullable=False)

    run = relationship('ObservingRun', back_populates='assignments')
    run_id = sa.Column(sa.ForeignKey('observingruns.id', ondelete='CASCADE'),
                       nullable=False, index=True)

    @hybrid_property
    def instrument(self):
        return self.run.instrument

    @property
    def rise_time(self):
        """The time at which the object rises on this run."""
        observer = self.instrument.telescope.observer
        target = self.obj.target
        return observer.target_rise_time(self.run.sunset, target,
                                         which='next',
                                         horizon=30 * u.degree)

    @property
    def set_time(self):
        """The time at which the object sets on this run."""
        observer = self.instrument.telescope.observer
        target = self.obj.target
        return observer.target_set_time(self.rise_time, target,
                                        which='next',
                                        horizon=30 * u.degree)


User.assignments = relationship('ClassicalAssignment', back_populates='requester')

class Event(Base):
    """Event information, including an event ID, mission, and time of the
    event"""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    dateobs = sa.Column(
        sa.DateTime,
        comment='Event time',
        unique=True,
        nullable=False)

    gcn_notices = relationship(
        lambda: GcnNotice,
        order_by=lambda: GcnNotice.date)

    _tags = relationship(
        lambda: Tag,
        order_by=lambda: (
            sa.func.lower(Tag.text).notin_({'fermi', 'swift', 'amon', 'lvc'}),
            sa.func.lower(Tag.text).notin_({'long', 'short'}),
            sa.func.lower(Tag.text).notin_({'grb', 'gw', 'transient'})
        )
    )

    tags = association_proxy(
        '_tags',
        'text',
        creator=lambda tag: Tag(text=tag))

    localizations = relationship(lambda: Localization)

    plans = relationship(lambda: Plan, backref='event')

    @hybrid_property
    def retracted(self):
        return 'retracted' in self.tags

    @retracted.expression
    def retracted(cls):
        return sa.literal('retracted').in_(cls.tags)

    @property
    def lightcurve(self):
        try:
            notice = self.gcn_notices[0]
        except IndexError:
            return None
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='LightCurve_URL']")
        if elem is None:
            return None
        else:
            return elem.attrib.get('value', '').replace('http://', 'https://')

    @property
    def gracesa(self):
        try:
            notice = self.gcn_notices[0]
        except IndexError:
            return None
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='EventPage']")
        if elem is None:
            return None
        else:
            return elem.attrib.get('value', '')


    @property
    def ned_gwf(self):
        return "https://ned.ipac.caltech.edu/gwf/events"

    @property
    def HasNS(self):
        notice = self.gcn_notices[0]
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='HasNS']")
        if elem is None:
            return None
        else:
            return 'HasNS: '+elem.attrib.get('value', '')

    @property
    def HasRemnant(self):
        notice = self.gcn_notices[0]
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='HasRemnant']")
        if elem is None:
            return None
        else:
            return 'HasRemnant: '+elem.attrib.get('value', '')

    @property
    def FAR(self):
        notice = self.gcn_notices[0]
        root = lxml.etree.fromstring(notice.content)
        elem = root.find(".//Param[@name='FAR']")
        if elem is None:
            return None
        else:
            return 'FAR: '+elem.attrib.get('value', '')


class EventView(Base):
    event_id = sa.Column(sa.ForeignKey('events.id', ondelete='CASCADE'),
                         nullable=False, unique=False)
    username_or_token_id = sa.Column(sa.String, nullable=False, unique=False)
    is_token = sa.Column(sa.Boolean, nullable=False, default=False)
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.now,
                           index=True)


class Tag(Base):
    """Store qualitative tags for events."""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    dateobs = sa.Column(
        sa.DateTime,
        sa.ForeignKey(Event.dateobs),
        nullable=False,
        primary_key=True)

    text = sa.Column(
        sa.Unicode,
        nullable=False,
        primary_key=True)


class Tele(Base):
    """Telescope information"""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    telescope = sa.Column(
        sa.String,
        primary_key=True,
        unique=True,
        comment='Telescope name')

    lat = sa.Column(
        sa.Float,
        nullable=False,
        comment='Latitude')

    lon = sa.Column(
        sa.Float,
        nullable=False,
        comment='Longitude')

    elevation = sa.Column(
        sa.Float,
        nullable=False,
        comment='Elevation')

    timezone = sa.Column(
        sa.String,
        nullable=False,
        comment='Time zone')

    filters = sa.Column(
        sa.ARRAY(sa.String),
        nullable=False,
        comment='Available filters')

    fields = relationship(lambda: Field)

    plans = relationship(lambda: Plan)

    default_plan_args = sa.Column(
        sa.JSON,
        nullable=False,
        comment='Default plan arguments')


class Field(Base):
    """Footprints and number of observations in each filter for standard PTF
    tiles"""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    telescope = sa.Column(
        sa.String,
        sa.ForeignKey(Tele.telescope),
        primary_key=True,
        comment='Telescope')

    field_id = sa.Column(
        sa.Integer,
        primary_key=True,
        unique=True,
        comment='Field ID')

    ra = sa.Column(
        sa.Float,
        nullable=False,
        comment='RA of field center')

    dec = sa.Column(
        sa.Float,
        nullable=False,
        comment='Dec of field center')

    contour = sa.Column(
        sa.JSON,
        nullable=False,
        comment='GeoJSON contours')

    reference_filter_ids = sa.Column(
        sa.ARRAY(sa.Integer),
        nullable=False,
        comment='Reference filter IDs')

    reference_filter_mags = sa.Column(
        sa.ARRAY(sa.Float),
        nullable=False,
        comment='Reference filter magss')

    ipix = sa.Column(
        sa.ARRAY(sa.Integer),
        comment='Healpix indices')

    subfields = relationship(lambda: SubField)


class SubField(Base):
    """SubFields"""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    telescope = sa.Column(
        sa.String,
        sa.ForeignKey(Tele.telescope),
        primary_key=True,
        comment='Telescope')

    field_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(Field.field_id),
        primary_key=True,
        comment='Field ID')

    subfield_id = sa.Column(
        sa.Integer,
        primary_key=True,
        comment='SubField ID')

    ipix = sa.Column(
        sa.ARRAY(sa.Integer),
        comment='Healpix indices')


class GcnNotice(Base):
    """Records of ingested GCN notices"""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    ivorn = sa.Column(
        sa.String,
        primary_key=True,
        comment='Unique identifier of VOEvent')

    notice_type = sa.Column(
        sa.Enum(gcn.NoticeType, native_enum=False),
        nullable=False,
        comment='GCN Notice type')

    stream = sa.Column(
        sa.String,
        nullable=False,
        comment='Event stream or mission (i.e., "Fermi")')

    date = sa.Column(
        sa.DateTime,
        nullable=False,
        comment='UTC message timestamp')

    dateobs = sa.Column(
        sa.DateTime,
        sa.ForeignKey(Event.dateobs),
        nullable=False,
        comment='UTC event timestamp')

    content = deferred(sa.Column(
        sa.LargeBinary,
        nullable=False,
        comment='Raw VOEvent content'))

    def _get_property(self, property_name, value=None):
        root = lxml.etree.fromstring(self.content)
        path = ".//Param[@name='{}']".format(property_name)
        elem = root.find(path)
        value = float(elem.attrib.get('value', '')) * 100
        return value

    @property
    def has_ns(self):
        return self._get_property(property_name="HasNS")

    @property
    def has_remnant(self):
        return self._get_property(property_name="HasRemnant")

    @property
    def far(self):
        return self._get_property(property_name="FAR")

    @property
    def bns(self):
        return self._get_property(property_name="BNS")

    @property
    def nsbh(self):
        return self._get_property(property_name="NSBH")

    @property
    def bbh(self):
        return self._get_property(property_name="BBH")

    @property
    def mass_gap(self):
        return self._get_property(property_name="MassGap")

    @property
    def noise(self):
        return self._get_property(property_name="Terrestrial")


class Localization(Base):
    """Localization information, including the localization ID, event ID, right
    ascension, declination, error radius (if applicable), and the healpix
    map."""

    nside = 512
    """HEALPix resolution used for flat (non-multiresolution) operations."""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    dateobs = sa.Column(
        sa.DateTime,
        sa.ForeignKey(Event.dateobs),
        nullable=False,
        comment='UTC event timestamp')

    localization_name = sa.Column(
        sa.String,
        primary_key=True,
        comment='Localization name')

    uniq = deferred(sa.Column(
        sa.ARRAY(sa.BigInteger),
        nullable=False,
        comment='Multiresolution HEALPix UNIQ pixel index array'))

    probdensity = deferred(sa.Column(
        sa.ARRAY(sa.Float),
        nullable=False,
        comment='Multiresolution HEALPix probability density array'))

    distmu = deferred(sa.Column(
        sa.ARRAY(sa.Float),
        comment='Multiresolution HEALPix distance mu array'))

    distsigma = deferred(sa.Column(
        sa.ARRAY(sa.Float),
        comment='Multiresolution HEALPix distance sigma array'))

    distnorm = deferred(sa.Column(
        sa.ARRAY(sa.Float),
        comment='Multiresolution HEALPix distance normalization array'))

    contour = deferred(sa.Column(
        sa.JSON,
        comment='GeoJSON contours'))

    @hybrid_property
    def is_3d(self):
        return (self.distmu is not None and
                self.distsigma is not None and
                self.distnorm is not None)

    @is_3d.expression
    def is_3d(self):
        return (self.distmu.isnot(None) and
                self.distsigma.isnot(None) and
                self.distnorm.isnot(None))

    @property
    def table_2d(self):
        """Get multiresolution HEALPix dataset, probability density only."""
        return table.Table(
            [np.asarray(self.uniq, dtype=np.int64), self.probdensity],
            names=['UNIQ', 'PROBDENSITY'])

    @property
    def table(self):
        """Get multiresolution HEALPix dataset, probability density and
        distance."""
        if self.is_3d:
            return table.Table(
                [
                    np.asarray(self.uniq, dtype=np.int64),
                    self.probdensity, self.distmu,
                    self.distsigma, self.distnorm],
                names=[
                    'UNIQ', 'PROBDENSITY', 'DISTMU', 'DISTSIGMA', 'DISTNORM'])
        else:
            return self.table_2d

    @property
    def flat_2d(self):
        """Get flat resolution HEALPix dataset, probability density only."""
        order = hp.nside2order(Localization.nside)
        result = rasterize(self.table_2d, order)['PROB']
        return hp.reorder(result, 'NESTED', 'RING')

    @property
    def flat(self):
        """Get flat resolution HEALPix dataset, probability density and
        distance."""
        if self.is_3d:
            order = hp.nside2order(Localization.nside)
            t = rasterize(self.table, order)
            result = t['PROB'], t['DISTMU'], t['DISTSIGMA'], t['DISTNORM']
            return hp.reorder(result, 'NESTED', 'RING')
        else:
            return self.flat_2d,

class Plan(Base):
    """Tiling information, including the event time, localization ID, tile IDs,
    and plan name"""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    dateobs = sa.Column(
        sa.DateTime,
        sa.ForeignKey(Event.dateobs),
        primary_key=True,
        comment='UTC event timestamp')

    telescope = sa.Column(
        sa.String,
        sa.ForeignKey(Tele.telescope),
        primary_key=True,
        comment='Telescope')

    plan_name = sa.Column(
        sa.String,
        primary_key=True,
        unique=True,
        comment='Plan name')

    validity_window_start = sa.Column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now(),
        comment='Start of validity window')

    validity_window_end = sa.Column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now() + timedelta(1),
        comment='End of validity window')

    plan_args = sa.Column(
        sa.JSON,
        nullable=False,
        comment='Plan arguments')

    # FIXME: Hard-code program_id, filter_id, subprogram_name
    program_id = 2

    class Status(enum.IntEnum):
        WORKING = 0
        READY = 1
        SUBMITTED = 2

    status = sa.Column(
        sa.Enum(Status),
        default=Status.WORKING,
        nullable=False,
        comment='Plan status')

    planned_observations = relationship(
        'PlannedObservation', backref='plan',
        order_by=lambda: PlannedObservation.obstime)

    @property
    def start_observation(self):
        """Time of the first planned observation."""
        if self.planned_observations:
            return self.planned_observations[0].obstime
        else:
            return None

    @hybrid_property
    def num_observations(self):
        """Number of planned observation."""
        return len(self.planned_observations)

    @num_observations.expression
    def num_observations(cls):
        """Number of planned observation."""
        return cls.planned_observations.count()

    @property
    def num_observations_per_filter(self):
        """Number of planned observation per filter."""
        filters = list(Telescope.query.get(self.telescope).filters)
        nepochs = np.zeros(len(filters),)
        bands = {1: 'g', 2: 'r', 3: 'i', 4: 'z', 5: 'J'}
        for planned_observation in self.planned_observations:
            filt = bands[planned_observation.filter_id]
            idx = filters.index(filt)
            nepochs[idx] = nepochs[idx] + 1
        nobs_per_filter = []
        for ii, filt in enumerate(filters):
            nobs_per_filter.append("%s: %d" % (filt, nepochs[ii]))
        return " ".join(nobs_per_filter)

    @property
    def total_time(self):
        """Total observation time (seconds)."""
        return sum(_.exposure_time for _ in self.planned_observations)

    @property
    def tot_time_with_overheads(self):
        overhead = sum(
            _.overhead_per_exposure for _ in self.planned_observations)
        return overhead + self.total_time

    @property
    def ipix(self):
        return {
            i for planned_observation in self.planned_observations
            if planned_observation.field.ipix is not None
            for i in planned_observation.field.ipix}

    @property
    def area(self):
        nside = Localization.nside
        return hp.nside2pixarea(nside, degrees=True) * len(self.ipix)

    def get_probability(self, localization):
        ipix = np.asarray(list(self.ipix))
        if len(ipix) > 0:
            return localization.flat_2d[ipix].sum()
        else:
            return 0.0


class PlannedObservation(Base):
    """Tile information, including the event time, localization ID, field IDs,
    tiling name, and tile probabilities."""

    id = sa.Column(sa.Integer , primary_key=True , autoincrement=True)

    planned_observation_id = sa.Column(
        sa.Integer,
        primary_key=True,
        comment='Exposure ID')

    dateobs = sa.Column(
        sa.DateTime,
        sa.ForeignKey(Event.dateobs),
        primary_key=True,
        comment='UTC event timestamp')

    telescope = sa.Column(
        sa.String,
        sa.ForeignKey(Tele.telescope),
        primary_key=True,
        comment='Telescope')

    field_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(Field.field_id),
        primary_key=True,
        comment='Field ID')

    plan_name = sa.Column(
        sa.String,
        sa.ForeignKey(Plan.plan_name),
        primary_key=True,
        comment='Plan name')

    field = relationship(Field, viewonly=True)

    exposure_time = sa.Column(
        sa.Integer,
        nullable=False,
        comment='Exposure time in seconds')

    # FIXME: remove
    weight = sa.Column(
        sa.Float,
        nullable=False,
        comment='Weight associated with each observation')

    filter_id = sa.Column(
        sa.Integer,
        nullable=False,
        comment='Filter ID (g=1, r=2, i=3, z=4, J=5)')

    obstime = sa.Column(
        sa.DateTime,
        nullable=False,
        comment='UTC observation timestamp')

    overhead_per_exposure = sa.Column(
        sa.Integer,
        nullable=False,
        comment='Overhead time per exposure in seconds')

schema.setup_schema()
