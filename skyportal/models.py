from datetime import datetime
import numpy as np

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import relationship, joinedload
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_utils import ArrowType
from sqlalchemy.ext.hybrid import hybrid_property

from baselayer.app.models import (init_db, join_model, Base, DBSession, ACL,
                                  Role, User, Token)
from baselayer.app.custom_exceptions import AccessError

from . import schema

from sncosmo.bandpasses import _BANDPASSES
from sncosmo.magsystems import _MAGSYSTEMS

ALLOWED_MAGSYSTEMS = tuple(l['name'] for l in _MAGSYSTEMS.get_loaders_metadata())
ALLOWED_BANDPASSES = tuple(l['name'] for l in _BANDPASSES.get_loaders_metadata())

allowed_magsystems = sa.Enum(*ALLOWED_MAGSYSTEMS, name="zpsys", validate_strings=True)
allowed_bandpasses = sa.Enum(*ALLOWED_BANDPASSES, name="bandpasses", validate_strings=True)

FIDUCIAL_ZP = 25.


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

    last_detected = sa.Column(ArrowType, nullable=True)
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
Candidate.passing_alert_id = sa.Column(sa.Integer)


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


Candidate.get_if_owned_by = get_candidate_if_owned_by
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


# Not used in get_source_if_owned_by, but defined in case it's called elsewhere
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
Source.get_if_owned_by = get_source_if_owned_by

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
    lat = sa.Column(sa.Float, nullable=False)
    lon = sa.Column(sa.Float, nullable=False)
    elevation = sa.Column(sa.Float, nullable=False)
    diameter = sa.Column(sa.Float, nullable=False)

    groups = relationship('Group', secondary='group_telescopes')
    instruments = relationship('Instrument', back_populates='telescope',
                               cascade='save-update, merge, refresh-expire, expunge',
                               passive_deletes=True)


GroupTelescope = join_model('group_telescopes', Group, Telescope)

import re
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import cast


class ArrayOfEnum(ARRAY):
    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)

    def result_processor(self, dialect, coltype):
        super_rp = super(ArrayOfEnum, self).result_processor(dialect, coltype)

        def handle_raw_string(value):
            if value==None:
                return []
            inner = re.match(r"^{(.*)}$", value).group(1)
            return inner.split(",")

        def process(value):
            return super_rp(handle_raw_string(value))
        return process


class Instrument(Base):

    name = sa.Column(sa.String, nullable=False)
    modes = sa.Column(psql.ARRAY(instrument_modes), nullable=False)

    # example
    # name: 'ZTF'
    # modes: ['imaging']
    # properties: {'imaging': {'filters': ['ztfg', 'ztfr', 'ztfi']}}

    properties = sa.Column(psql.JSONB, nullable=False)

    telescope_id = sa.Column(sa.ForeignKey('telescopes.id',
                                           ondelete='CASCADE'),
                             nullable=False, index=True)
    telescope = relationship('Telescope', back_populates='instruments')

    followup_requests = relationship('FollowupRequest',
                                     back_populates='instrument')

    photometry = relationship('Photometry', back_populates='instrument')
    spectra = relationship('Spectrum', back_populates='instrument')

    # can be [] if an instrument is spec only
    filters = sa.Column(ArrayOfEnum(allowed_bandpasses), nullable=False)


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


class Photometry(Base):
    __tablename__ = 'photometry'

    mjd = sa.Column(sa.Float, nullable=False)  # mjd date
    flux = sa.Column(sa.Float)
    fluxerr = sa.Column(sa.Float, nullable=False)
    zp = sa.Column(sa.Float, nullable=False)
    zpsys = sa.Column(allowed_magsystems, nullable=False)
    filter = sa.Column(allowed_bandpasses, nullable=False)

    ra = sa.Column(sa.Float)
    dec = sa.Column(sa.Float)


    isdiffpos = sa.Column(sa.Boolean, default=True)  # candidate from position?

    var_mag = sa.Column(sa.Float, nullable=True)
    var_e_mag = sa.Column(sa.Float, nullable=True)

    dist_nearest_source = sa.Column(sa.Float, nullable=True)
    mag_nearest_source = sa.Column(sa.Float, nullable=True)
    e_mag_nearest_source = sa.Column(sa.Float, nullable=True)

    # external values
    score = sa.Column(sa.Float, nullable=True)  # RB
    candid = sa.Column(sa.BigInteger, nullable=True)  # candidate ID
    altdata = sa.Column(JSONB)

    origin = sa.Column(sa.String, nullable=True)

    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    obj = relationship('Obj', back_populates='photometry')
    instrument_id = sa.Column(sa.ForeignKey('instruments.id'),
                              nullable=False, index=True)
    instrument = relationship('Instrument', back_populates='photometry')
    thumbnails = relationship('Thumbnail', passive_deletes=True)

    @hybrid_property
    def mag(self):
        if self.flux > 0 and self.zp is not None:
            return -2.5 * np.log10(self.flux) + self.zp
        else:
            return None

    @hybrid_property
    def e_mag(self):
        if self.flux > 0 and self.fluxerr > 0:
            return 2.5 / np.log(10) * self.fluxerr / self.flux
        else:
            return None

    @mag.expression
    def mag(cls):
        return sa.case(
            [
                (sa.and_(cls.flux > 0, cls.zp.isnot(None)),
                 -2.5 * sa.func.log(cls.flux) + cls.zp),
            ],
            else_=None
        )

    @e_mag.expression
    def e_mag(cls):
        return sa.case(
            [
                (sa.and_(cls.flux > 0, cls.fluxerr > 0),
                 2.5 / sa.func.ln(10) * cls.fluxerr / cls.flux)
            ],
            else_=None
        )


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
    type = sa.Column(sa.Enum('new', 'ref', 'sub', 'sdss', 'dr8', "new_gz",
                             'ref_gz', 'sub_gz',
                             name='thumbnail_types', validate_strings=True))
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
