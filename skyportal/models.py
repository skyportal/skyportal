import arrow
import uuid
import re
from datetime import datetime
import numpy as np
import sqlalchemy as sa
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils import ArrowType, URLType

from astropy.time import Time

from baselayer.app.models import (init_db, join_model, Base, DBSession, ACL,
                                  Role, User, Token)
from baselayer.app.custom_exceptions import AccessError

from . import schema
from .phot_enum import allowed_bandpasses, thumbnail_types


# In the AB system, a brightness of 23.9 mag corresponds to 1 microJy. Using this
# will put our converted fluxes to microJy.
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
        return bool(set(self.groups) & set(user_or_token.groups))
    if hasattr(self, 'group'):
        return self.group in user_or_token.groups
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
                           back_populates='groups')
    telescopes = relationship('Telescope', secondary='group_telescopes')
    group_users = relationship('GroupUser', back_populates='group',
                               cascade='save-update, merge, refresh-expire, expunge',
                               passive_deletes=True)
    users = relationship('User', secondary='group_users',
                         back_populates='groups')
    filter = relationship("Filter", uselist=False, back_populates="group")
    photometry = relationship("Photometry", secondary="group_photometry",
                              back_populates="groups",
                              cascade="save-update, merge, refresh-expire, expunge")


GroupUser = join_model('group_users', Group, User)
GroupUser.admin = sa.Column(sa.Boolean, nullable=False, default=False)


class Stream(Base):
    name = sa.Column(sa.String, unique=True, nullable=False)
    url = sa.Column(sa.String, unique=True, nullable=False)
    username = sa.Column(sa.String)
    password = sa.Column(sa.String)

    groups = relationship('Group', secondary='stream_groups',
                          back_populates='streams')


StreamGroup = join_model('stream_groups', Stream, Group)


User.group_users = relationship('GroupUser', back_populates='user',
                                cascade='save-update, merge, refresh-expire, expunge',
                                passive_deletes=True)
User.groups = relationship('Group', secondary='group_users',
                           back_populates='users')


@property
def token_groups(self):
    return self.created_by.groups


Token.groups = token_groups


class Obj(Base):
    id = sa.Column(sa.String, primary_key=True)
    # TODO should this column type be decimal? fixed-precison numeric
    ra = sa.Column(sa.Float)
    dec = sa.Column(sa.Float)

    ra_dis = sa.Column(sa.Float)
    dec_dis = sa.Column(sa.Float)

    ra_err = sa.Column(sa.Float, nullable=True)
    dec_err = sa.Column(sa.Float, nullable=True)

    offset = sa.Column(sa.Float, default=0.0)
    redshift = sa.Column(sa.Float, nullable=True)

    # Contains all external metadata, e.g. simbad, pan-starrs, tns, gaia
    altdata = sa.Column(JSONB, nullable=True)

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
                            order_by="Classification.created_at"
                      )

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
                              cascade='save-update, merge, refresh-expire, expunge')

    followup_requests = relationship('FollowupRequest', back_populates='obj')

    @hybrid_property
    def last_detected(self):
        return max(phot.iso for phot in self.photometry if phot.snr > 5)

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


class Filter(Base):
    query_string = sa.Column(sa.String, nullable=False, unique=False)
    group_id = sa.Column(sa.ForeignKey("groups.id"))
    group = relationship("Group", foreign_keys=[group_id], back_populates="filter")


Candidate = join_model("candidates", Filter, Obj)
Candidate.passed_at = sa.Column(sa.DateTime, nullable=True)
Candidate.passing_alert_id = sa.Column(sa.BigInteger)


def get_candidate_if_owned_by(obj_id, user_or_token, options=[]):
    if Candidate.query.filter(Candidate.obj_id == obj_id).first() is None:
        return None
    user_group_ids = [g.id for g in user_or_token.groups]
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
    return self.filter.group in user_or_token.groups


Candidate.get_obj_if_owned_by = get_candidate_if_owned_by
Candidate.is_owned_by = candidate_is_owned_by


Source = join_model("sources", Group, Obj)
"""User.sources defines the logic for whether a user has access to a source;
   if this gets more complicated it should become a function/`hybrid_property`
   rather than a `relationship`.
"""
Source.saved_by_id = sa.Column(sa.ForeignKey("users.id"), nullable=True, unique=False)
Source.saved_by = relationship("User", foreign_keys=[Source.saved_by_id],
                               backref="saved_sources")
Source.saved_at = sa.Column(sa.DateTime, nullable=True)
Source.active = sa.Column(sa.Boolean, server_default="true")
Source.requested = sa.Column(sa.Boolean, server_default="false")
Source.unsaved_by_id = sa.Column(sa.ForeignKey("users.id"), nullable=True, unique=False)
Source.unsaved_by = relationship("User", foreign_keys=[Source.unsaved_by_id])


def source_is_owned_by(self, user_or_token):
    source_group_ids = [row[0] for row in DBSession.query(
        Source.group_id).filter(Source.obj_id == self.obj_id).all()]
    return bool(set(source_group_ids) & {g.id for g in user_or_token.groups})


def get_source_if_owned_by(obj_id, user_or_token, options=[]):
    if Source.query.filter(Source.obj_id == obj_id).first() is None:
        return None
    user_group_ids = [g.id for g in user_or_token.groups]
    s = (Source.query.filter(Source.obj_id == obj_id)
         .filter(Source.group_id.in_(user_group_ids)).options(options).first())
    if s is None:
        raise AccessError("Insufficient permissions.")
    return s.obj


Source.is_owned_by = source_is_owned_by
Source.get_obj_if_owned_by = get_source_if_owned_by


def get_obj_if_owned_by(obj_id, user_or_token, options=[]):
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


def get_photometry_owned_by_user(obj_id, user_or_token):
    return (
        Photometry.query.filter(Photometry.obj_id == obj_id)
        .filter(
            Photometry.groups.any(Group.id.in_([g.id for g in user_or_token.groups]))
        )
        .all()
    )


Obj.get_photometry_owned_by_user = get_photometry_owned_by_user


User.sources = relationship('Obj', backref='users',
                            secondary='join(Group, sources).join(group_users)',
                            primaryjoin='group_users.c.user_id == users.c.id')


class SourceView(Base):
    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, unique=False)
    username_or_token_id = sa.Column(sa.String, nullable=False, unique=False)
    is_token = sa.Column(sa.Boolean, nullable=False, default=False)
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.now,
                           index=True)


class Telescope(Base):
    name = sa.Column(sa.String, nullable=False)
    nickname = sa.Column(sa.String, nullable=False)
    lat = sa.Column(sa.Float, nullable=False, doc='Latitude in deg.')
    lon = sa.Column(sa.Float, nullable=False, doc='Longitude in deg.')
    elevation = sa.Column(sa.Float, nullable=False, doc='Elevation in meters.')
    diameter = sa.Column(sa.Float, nullable=False, doc='Diameter in meters.')
    skycam_link = sa.Column(URLType, nullable=True,
                            doc="Link to the telescope's sky camera.")

    groups = relationship('Group', secondary='group_telescopes')
    instruments = relationship('Instrument', back_populates='telescope',
                               cascade='save-update, merge, refresh-expire, expunge',
                               passive_deletes=True)


GroupTelescope = join_model('group_telescopes', Group, Telescope)


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
    name = sa.Column(sa.String, nullable=False)
    type = sa.Column(sa.String)
    band = sa.Column(sa.String)
    telescope_id = sa.Column(sa.ForeignKey('telescopes.id',
                                           ondelete='CASCADE'),
                             nullable=False, index=True)
    telescope = relationship('Telescope', back_populates='instruments')

    followup_requests = relationship('FollowupRequest',
                                     back_populates='instrument')

    photometry = relationship('Photometry', back_populates='instrument')
    spectra = relationship('Spectrum', back_populates='instrument')

    # can be [] if an instrument is spec only
    filters = sa.Column(ArrayOfEnum(allowed_bandpasses), nullable=True,
                        default=[])


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

    allowed_classes = sa.Column(sa.ARRAY(sa.String), nullable=False,
                                doc="Computed list of allowable classes"
                                " in this taxonomy.")

    isLatest = sa.Column(sa.Boolean, default=True, nullable=False,
                         doc='Consider this the latest version of '
                             'the taxonomy with this name? Defaults '
                             'to True.'
                         )
    groups = relationship("Group", secondary="group_taxonomy",
                          cascade="save-update,"
                                  "merge, refresh-expire, expunge"
                          )


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
    ctype = sa.Column(sa.Enum('text', 'redshift', 'classification',
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
                          cascade="save-update, merge, refresh-expire, expunge")


GroupComment = join_model("group_comments", Group, Comment)


class Classification(Base):
    classification = sa.Column(sa.String, nullable=False)
    taxonomy_id = sa.Column(sa.ForeignKey('taxonomies.id'),
                            nullable=False)
    probability = sa.Column(sa.Float,
                            doc='User-assigned probability of belonging '
                            'to this class', nullable=True)

    author = sa.Column(sa.String, nullable=False)
    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    obj = relationship('Obj', back_populates='classifications')
    groups = relationship("Group", secondary="group_classifications",
                          cascade="save-update, merge, refresh-expire, expunge")


GroupClassifications = join_model("group_classifications", Group, Classification)


class Photometry(Base):
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

    ra = sa.Column(sa.Float, doc='ICRS Right Ascension of the centroid '
                                 'of the photometric aperture [deg].')
    dec = sa.Column(sa.Float, doc='ICRS Declination of the centroid of '
                                  'the photometric aperture [deg].')

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
                          cascade="save-update, merge, refresh-expire, expunge")
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

    @classmethod
    def from_ascii(cls, filename, obj_id, instrument_id, observed_at):
        data = np.loadtxt(filename)
        if data.shape[1] != 2:  # TODO support other formats
            raise ValueError(f"Expected 2 columns, got {data.shape[1]}")

        return cls(wavelengths=data[:, 0], fluxes=data[:, 1],
                   obj_id=obj_id, instrument_id=instrument_id,
                   observed_at=observed_at)


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
                       secondary='photometry')


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

schema.setup_schema()
