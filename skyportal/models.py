from datetime import datetime
import os.path
import re
import requests
import numpy as np

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import backref, relationship, mapper
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_utils import ArrowType

from baselayer.app.models import (init_db, join_model, Base, DBSession, ACL,
                                  Role, User, Token)

from . import schema


def is_owned_by(self, user_or_token):
    """Generic ownership logic for any `skyportal` ORM model.

    Models with complicated ownership logic should implement their own method
    instead of adding too many additional conditions here.
    """
    if hasattr(self, 'tokens'):
        return (user_or_token in self.tokens)
    elif hasattr(self, 'groups'):
        return bool(set(self.groups) & set(user_or_token.groups))
    elif hasattr(self, 'users'):
        if hasattr(user_or_token, 'created_by'):
            if user_or_token.created_by in self.users:
                return True
        return (user_or_token in self.users)
    else:
        raise NotImplementedError(f"{type(self).__name__} object has no owner")
Base.is_owned_by = is_owned_by


class NumpyArray(sa.types.TypeDecorator):
    impl = psql.ARRAY(sa.Float)

    def process_result_value(self, value, dialect):
        return np.array(value)


class Group(Base):
    name = sa.Column(sa.String, unique=True, nullable=False)

    sources = relationship('Source', secondary='group_sources')
    streams = relationship('Stream', secondary='stream_groups',
                           back_populates='groups')
    telescopes = relationship('Telescope', secondary='group_telescopes')
    group_users = relationship('GroupUser', back_populates='group',
                               cascade='save-update, merge, refresh-expire, expunge',
                               passive_deletes=True)
    users = relationship('User', secondary='group_users',
                         back_populates='groups')


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


class Source(Base):
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

    altdata = sa.Column(JSONB, nullable=True)

    last_detected = sa.Column(ArrowType, nullable=True)
    dist_nearest_source = sa.Column(sa.Float, nullable=True)
    mag_nearest_source = sa.Column(sa.Float, nullable=True)
    e_mag_nearest_source = sa.Column(sa.Float, nullable=True)

    transient = sa.Column(sa.Boolean, default=False)
    varstar = sa.Column(sa.Boolean, default=False)
    is_roid = sa.Column(sa.Boolean, default=False)

    score = sa.Column(sa.Float, nullable=True)

    ## pan-starrs
    sgmag1 = sa.Column(sa.Float, nullable=True)
    srmag1 = sa.Column(sa.Float, nullable=True)
    simag1 = sa.Column(sa.Float, nullable=True)
    objectidps1 = sa.Column(sa.BigInteger, nullable=True)
    sgscore1 = sa.Column(sa.Float, nullable=True)
    distpsnr1 = sa.Column(sa.Float, nullable=True)

    origin = sa.Column(sa.String, nullable=True)
    modified = sa.Column(sa.DateTime, nullable=False,
                         server_default=sa.func.now(),
                         server_onupdate=sa.func.now())

    simbad_class = sa.Column(sa.Unicode, nullable=True, )
    simbad_info = sa.Column(JSONB, nullable=True)
    gaia_info = sa.Column(JSONB, nullable=True)
    tns_info = sa.Column(JSONB, nullable=True)
    tns_name = sa.Column(sa.Unicode, nullable=True)

    groups = relationship('Group', secondary='group_sources')
    comments = relationship('Comment', back_populates='source',
                            cascade='save-update, merge, refresh-expire, expunge',
                            passive_deletes=True,
                            order_by="Comment.created_at")
    photometry = relationship('Photometry', back_populates='source',
                              cascade='save-update, merge, refresh-expire, expunge',
                              single_parent=True,
                              passive_deletes=True,
                              order_by="Photometry.observed_at")

    detect_photometry_count = sa.Column(sa.Integer, nullable=True)

    spectra = relationship('Spectrum', back_populates='source',
                           cascade='save-update, merge, refresh-expire, expunge',
                           single_parent=True,
                           passive_deletes=True,
                           order_by="Spectrum.observed_at")
    thumbnails = relationship('Thumbnail', back_populates='source',
                              secondary='photometry',
                              cascade='save-update, merge, refresh-expire, expunge')

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
        return (f"http://skyservice.pha.jhu.edu/DR9/ImgCutout/getjpeg.aspx"
                f"?ra={self.ra}&dec={self.dec}&scale=0.3&width=200&height=200"
                f"&opt=G&query=&Grid=on")

    @property
    def desi_dr8_url(self):
        """Construct URL for public DESI DR8 cutout."""
        return (f"http://legacysurvey.org/viewer/jpeg-cutout?ra={self.ra}"
                f"&dec={self.dec}&size=200&layer=dr8&pixscale=0.262&bands=grz")


GroupSource = join_model('group_sources', Group, Source)
"""User.sources defines the logic for whether a user has access to a source;
   if this gets more complicated it should become a function/`hybrid_property`
   rather than a `relationship`.
"""
User.sources = relationship('Source', backref='users',
                            secondary='join(Group, group_sources).join(group_users)',
                            primaryjoin='group_users.c.user_id == users.c.id')


class SourceView(Base):
    source_id = sa.Column(sa.ForeignKey('sources.id', ondelete='CASCADE'),
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


class Instrument(Base):
    name = sa.Column(sa.String, nullable=False)
    type = sa.Column(sa.String, nullable=False)
    band = sa.Column(sa.String, nullable=False)

    telescope_id = sa.Column(sa.ForeignKey('telescopes.id',
                                           ondelete='CASCADE'),
                             nullable=False, index=True)
    telescope = relationship('Telescope', back_populates='instruments')
    photometry = relationship('Photometry', back_populates='instrument')
    spectra = relationship('Spectrum', back_populates='instrument')


class Comment(Base):
    text = sa.Column(sa.String, nullable=False)
    ctype = sa.Column(sa.Enum('text', 'redshift', 'classification',
                             name='comment_types', validate_strings=True))

    attachment_name = sa.Column(sa.String, nullable=True)
    attachment_type = sa.Column(sa.String, nullable=True)
    attachment_bytes = sa.Column(sa.types.LargeBinary, nullable=True)

    origin = sa.Column(sa.String, nullable=True)
    author = sa.Column(sa.String, nullable=False)
    source_id = sa.Column(sa.ForeignKey('sources.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    source = relationship('Source', back_populates='comments')


class Photometry(Base):
    __tablename__ = 'photometry'
    observed_at = sa.Column(ArrowType) # iso date
    mjd = sa.Column(sa.Float)  # mjd date
    time_format = sa.Column(sa.String, default='iso')
    time_scale = sa.Column(sa.String, default='utc')
    mag = sa.Column(sa.Float)
    e_mag = sa.Column(sa.Float)
    lim_mag = sa.Column(sa.Float)
    filter = sa.Column(sa.String)  # TODO Enum?
    isdiffpos = sa.Column(sa.Boolean, default=True)  # candidate from position?

    var_mag = sa.Column(sa.Float, nullable=True)
    var_e_mag = sa.Column(sa.Float, nullable=True)

    dist_nearest_source = sa.Column(sa.Float, nullable=True)
    mag_nearest_source = sa.Column(sa.Float, nullable=True)
    e_mag_nearest_source = sa.Column(sa.Float, nullable=True)

    ## external values
    score = sa.Column(sa.Float, nullable=True)  # RB
    candid = sa.Column(sa.BigInteger, nullable=True)  # candidate ID
    altdata = sa.Column(JSONB)

    origin = sa.Column(sa.String, nullable=True)

    source_id = sa.Column(sa.ForeignKey('sources.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    source = relationship('Source', back_populates='photometry')
    instrument_id = sa.Column(sa.ForeignKey('instruments.id'),
                              nullable=False, index=True)
    instrument = relationship('Instrument', back_populates='photometry')
    thumbnails = relationship('Thumbnail', passive_deletes=True)


class Spectrum(Base):
    __tablename__ = 'spectra'
    # TODO better numpy integration
    wavelengths = sa.Column(NumpyArray, nullable=False)
    fluxes = sa.Column(NumpyArray, nullable=False)
    errors = sa.Column(NumpyArray)

    source_id = sa.Column(sa.ForeignKey('sources.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    source = relationship('Source', back_populates='spectra')
    observed_at = sa.Column(sa.DateTime, nullable=False)
    origin = sa.Column(sa.String, nullable=True)
    # TODO program?
    instrument_id = sa.Column(sa.ForeignKey('instruments.id',
                                            ondelete='CASCADE'),
                              nullable=False, index=True)
    instrument = relationship('Instrument', back_populates='spectra')

    @classmethod
    def from_ascii(cls, filename, source_id, instrument_id, observed_at):
        data = np.loadtxt(filename)
        if data.shape[1] != 2:  # TODO support other formats
            raise ValueError(f"Expected 2 columns, got {data.shape[1]}")

        return cls(wavelengths=data[:, 0], fluxes=data[:, 1],
                   source_id=source_id, instrument_id=instrument_id,
                   observed_at=observed_at)


#def format_public_url(context):
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
    source = relationship('Source', back_populates='thumbnails', uselist=False,
                          secondary='photometry')


schema.setup_schema()
