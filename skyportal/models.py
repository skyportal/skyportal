import uuid
import re
from datetime import datetime, timezone
import arrow
import requests
from astropy import units as u
from astropy import time as ap_time
import astroplan
import numpy as np
import sqlalchemy as sa
from sqlalchemy import cast, event
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils import URLType, EmailType
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from astropy import coordinates as ap_coord
import healpix_alchemy as ha
import timezonefinder

from baselayer.app.models import (  # noqa
    init_db,
    join_model,
    Base,
    DBSession,
    ACL,
    Role,
    User,
    Token,
)
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.env import load_env
from baselayer.app.access import permissions


from . import schema
from .enum_types import (
    allowed_bandpasses,
    thumbnail_types,
    instrument_types,
    followup_priorities,
    api_classnames,
    followup_http_request_origins,
    listener_classnames,
)

from skyportal import facility_apis

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
    """SQLAlchemy representation of a NumPy array."""

    impl = psql.ARRAY(sa.Float)

    def process_result_value(self, value, dialect):
        return np.array(value)


class Group(Base):
    """A user group. `Group`s controls `User` access to `Filter`s and serve as
    targets for data sharing requests. `Photometry` and `Spectra` shared with
    a `Group` will be visible to all its members. `Group`s maintain specific
    `Stream` permissions. In order for a `User` to join a `Group`, the `User`
    must have access to all of the `Group`'s data `Stream`s.
    """

    name = sa.Column(sa.String, unique=True, nullable=False, doc='Name of the group.')

    streams = relationship(
        'Stream',
        secondary='group_streams',
        back_populates='groups',
        passive_deletes=True,
        doc='Stream access required for a User to become a member of the Group.',
    )
    filters = relationship(
        "Filter",
        back_populates="group",
        passive_deletes=True,
        doc='All filters (not just active) associated with a group.',
    )

    users = relationship(
        'User',
        secondary='group_users',
        back_populates='groups',
        passive_deletes=True,
        doc='The members of this group.',
    )

    group_users = relationship(
        'GroupUser',
        back_populates='group',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc='Elements of a join table mapping Users to Groups.',
    )

    observing_runs = relationship(
        'ObservingRun',
        back_populates='group',
        doc='The observing runs associated with this group.',
    )
    photometry = relationship(
        "Photometry",
        secondary="group_photometry",
        back_populates="groups",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='The photometry visible to this group.',
    )

    spectra = relationship(
        "Spectrum",
        secondary="group_spectra",
        back_populates="groups",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='The spectra visible to this group.',
    )
    single_user_group = sa.Column(
        sa.Boolean,
        default=False,
        doc='Flag indicating whether this group '
        'is a singleton group for one user only.',
    )
    allocations = relationship(
        'Allocation',
        back_populates="group",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Allocations made to this group.",
    )


GroupUser = join_model('group_users', Group, User)
GroupUser.__doc__ = "Join table mapping `Group`s to `User`s."

GroupUser.admin = sa.Column(
    sa.Boolean,
    nullable=False,
    default=False,
    doc="Boolean flag indicating whether the User is an admin of the group.",
)


class Stream(Base):
    """A data stream producing alerts that can be programmatically filtered using a Filter."""

    name = sa.Column(sa.String, unique=True, nullable=False, doc="Stream name.")
    altdata = sa.Column(
        JSONB,
        nullable=True,
        doc="Misc. metadata stored in JSON format, e.g. "
        "`{'collection': 'ZTF_alerts', selector: [1, 2]}`",
    )

    groups = relationship(
        'Group',
        secondary='group_streams',
        back_populates='streams',
        passive_deletes=True,
        doc="The Groups with access to this Stream.",
    )
    users = relationship(
        'User',
        secondary='stream_users',
        back_populates='streams',
        passive_deletes=True,
        doc="The users with access to this stream.",
    )
    filters = relationship(
        'Filter',
        back_populates='stream',
        passive_deletes=True,
        doc="The filters with access to this stream.",
    )


GroupStream = join_model('group_streams', Group, Stream)
GroupStream.__doc__ = "Join table mapping Groups to Streams."


StreamUser = join_model('stream_users', Stream, User)
StreamUser.__doc__ = "Join table mapping Streams to Users."


User.groups = relationship(
    'Group',
    secondary='group_users',
    back_populates='users',
    passive_deletes=True,
    doc="The Groups this User is a member of.",
)


User.streams = relationship(
    'Stream',
    secondary='stream_users',
    back_populates='users',
    passive_deletes=True,
    doc="The Streams this User has access to.",
)


@property
def user_or_token_accessible_groups(self):
    """Return the list of Groups a User or Token has access to. For non-admin
    Users or Token owners, this corresponds to the Groups they are a member of.
    For System Admins, this corresponds to all Groups."""
    if "System admin" in [acl.id for acl in self.acls]:
        return Group.query.all()
    return self.groups


User.accessible_groups = user_or_token_accessible_groups
Token.accessible_groups = user_or_token_accessible_groups


@property
def token_groups(self):
    """The groups the Token owner is a member of."""
    return self.created_by.groups


Token.groups = token_groups


class Obj(Base, ha.Point):
    """A record of an astronomical Object and its metadata, such as position,
    positional uncertainties, name, and redshift. Permissioning rules,
    such as group ownership, user visibility, etc., are managed by other
    entities, namely Source and Candidate."""

    id = sa.Column(sa.String, primary_key=True, doc="Name of the object.")
    # TODO should this column type be decimal? fixed-precison numeric

    ra_dis = sa.Column(sa.Float, doc="J2000 Right Ascension at discovery time [deg].")
    dec_dis = sa.Column(sa.Float, doc="J2000 Declination at discovery time [deg].")

    ra_err = sa.Column(
        sa.Float,
        nullable=True,
        doc="Error on J2000 Right Ascension at discovery time [deg].",
    )
    dec_err = sa.Column(
        sa.Float,
        nullable=True,
        doc="Error on J2000 Declination at discovery time [deg].",
    )

    offset = sa.Column(
        sa.Float, default=0.0, doc="Offset from nearest static object [arcsec]."
    )
    redshift = sa.Column(sa.Float, nullable=True, doc="Redshift.")

    # Contains all external metadata, e.g. simbad, pan-starrs, tns, gaia
    altdata = sa.Column(
        JSONB,
        nullable=True,
        doc="Misc. alternative metadata stored in JSON format, e.g. "
        "`{'gaia': {'info': {'Teff': 5780}}}`",
    )

    dist_nearest_source = sa.Column(
        sa.Float, nullable=True, doc="Distance to the nearest Obj [arcsec]."
    )
    mag_nearest_source = sa.Column(
        sa.Float, nullable=True, doc="Magnitude of the nearest Obj [AB]."
    )
    e_mag_nearest_source = sa.Column(
        sa.Float, nullable=True, doc="Error on magnitude of the nearest Obj [mag]."
    )

    transient = sa.Column(
        sa.Boolean,
        default=False,
        doc="Boolean indicating whether the object is an astrophysical transient.",
    )
    varstar = sa.Column(
        sa.Boolean,
        default=False,
        doc="Boolean indicating whether the object is a variable star.",
    )
    is_roid = sa.Column(
        sa.Boolean,
        default=False,
        doc="Boolean indicating whether the object is a moving object.",
    )

    score = sa.Column(sa.Float, nullable=True, doc="Machine learning score.")

    origin = sa.Column(sa.String, nullable=True, doc="Origin of the object.")

    internal_key = sa.Column(
        sa.String,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        doc="Internal key used for secure websocket messaging.",
    )

    comments = relationship(
        'Comment',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        order_by="Comment.created_at",
        doc="Comments posted about the object.",
    )

    classifications = relationship(
        'Classification',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        order_by="Classification.created_at",
        doc="Classifications of the object.",
    )

    photometry = relationship(
        'Photometry',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge',
        single_parent=True,
        passive_deletes=True,
        order_by="Photometry.mjd",
        doc="Photometry of the object.",
    )

    detect_photometry_count = sa.Column(
        sa.Integer,
        nullable=True,
        doc="How many times the object was detected above :math:`S/N = 5`.",
    )

    spectra = relationship(
        'Spectrum',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge',
        single_parent=True,
        passive_deletes=True,
        order_by="Spectrum.observed_at",
        doc="Spectra of the object.",
    )
    thumbnails = relationship(
        'Thumbnail',
        back_populates='obj',
        secondary='photometry',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="Thumbnails of the object.",
    )

    followup_requests = relationship(
        'FollowupRequest',
        back_populates='obj',
        doc="Robotic follow-up requests of the object.",
    )
    assignments = relationship(
        'ClassicalAssignment',
        back_populates='obj',
        doc="Assignments of the object to classical observing runs.",
    )

    @hybrid_property
    def last_detected(self):
        """UTC ISO date at which the object was last detected above a S/N of 5."""
        detections = [phot.iso for phot in self.photometry if phot.snr and phot.snr > 5]
        return max(detections) if detections else None

    @last_detected.expression
    def last_detected(cls):
        """UTC ISO date at which the object was last detected above a S/N of 5."""
        return (
            sa.select([sa.func.max(Photometry.iso)])
            .where(Photometry.obj_id == cls.id)
            .where(Photometry.snr > 5.0)
            .group_by(Photometry.obj_id)
            .label('last_detected')
        )

    def add_linked_thumbnails(self):
        """Determine the URLs of the SDSS and DESI DR8 thumbnails of the object,
        insert them into the Thumbnails table, and link them to the object."""
        sdss_thumb = Thumbnail(
            photometry=self.photometry[0], public_url=self.sdss_url, type='sdss'
        )
        dr8_thumb = Thumbnail(
            photometry=self.photometry[0], public_url=self.desi_dr8_url, type='dr8'
        )
        DBSession().add_all([sdss_thumb, dr8_thumb])
        DBSession().commit()

    @property
    def sdss_url(self):
        """Construct URL for public Sloan Digital Sky Survey (SDSS) cutout."""
        return (
            f"http://skyserver.sdss.org/dr12/SkyserverWS/ImgCutout/getjpeg"
            f"?ra={self.ra}&dec={self.dec}&scale=0.3&width=200&height=200"
            f"&opt=G&query=&Grid=on"
        )

    @property
    def desi_dr8_url(self):
        """Construct URL for public DESI DR8 cutout."""
        return (
            f"http://legacysurvey.org/viewer/jpeg-cutout?ra={self.ra}"
            f"&dec={self.dec}&size=200&layer=dr8&pixscale=0.262&bands=grz"
        )

    @property
    def target(self):
        """Representation of the RA and Dec of this Obj as an
        astroplan.FixedTarget."""
        coord = ap_coord.SkyCoord(self.ra, self.dec, unit='deg')
        return astroplan.FixedTarget(name=self.id, coord=coord)

    @property
    def gal_lat_deg(self):
        """Get the galactic latitute of this object"""
        coord = ap_coord.SkyCoord(self.ra, self.dec, unit="deg")
        return coord.galactic.b.deg

    @property
    def gal_lon_deg(self):
        """Get the galactic longitude of this object"""
        coord = ap_coord.SkyCoord(self.ra, self.dec, unit="deg")
        return coord.galactic.l.deg

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
        airmass[above] = 1.0 / np.sin(np.deg2rad(sinarg[above]))

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
    """An alert filter that operates on a Stream. A Filter is associated
    with exactly one Group, and a Group may have multiple operational Filters.
    """

    name = sa.Column(sa.String, nullable=False, unique=False, doc="Filter name.")
    stream_id = sa.Column(
        sa.ForeignKey("streams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Filter's Stream.",
    )
    stream = relationship(
        "Stream",
        foreign_keys=[stream_id],
        back_populates="filters",
        doc="The Filter's Stream.",
    )
    group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Filter's Group.",
    )
    group = relationship(
        "Group",
        foreign_keys=[group_id],
        back_populates="filters",
        doc="The Filter's Group.",
    )


Candidate = join_model("candidates", Filter, Obj)
Candidate.__doc__ = (
    "An Obj that passed a Filter, becoming scannable on the " "Filter's scanning page."
)
Candidate.passed_at = sa.Column(
    sa.DateTime, nullable=True, doc="ISO UTC time when the Candidate passed the Filter."
)

Candidate.passing_alert_id = sa.Column(
    sa.BigInteger, doc="ID of the Stream alert that passed the Filter."
)


def get_candidate_if_owned_by(obj_id, user_or_token, options=[]):
    """Return an Obj from the database if the Obj is a Candidate in at least
    one of the requesting User or Token owner's accessible Groups. If the Obj is not a
    Candidate in one of the User or Token owner's accessible Groups, raise an AccessError.
    If the Obj does not exist, return `None`.

    Parameters
    ----------
    obj_id : integer or string
       Primary key of the Obj.
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.
    options : list of `sqlalchemy.orm.MapperOption`s
       Options that wil be passed to `options()` in the loader query.

    Returns
    -------
    obj : `skyportal.models.Obj`
       The requested Obj.
    """

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
    """Return a boolean indicating whether the Candidate passed the Filter
    of any of a User or Token owner's accessible Groups.


    Parameters
    ----------
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.

    Returns
    -------
    owned : bool
       Whether the Candidate is owned by the User or Token owner.
    """
    return self.filter.group in user_or_token.accessible_groups


Candidate.get_obj_if_owned_by = get_candidate_if_owned_by
Candidate.is_owned_by = candidate_is_owned_by


Source = join_model("sources", Group, Obj)
Source.__doc__ = (
    "An Obj that has been saved to a Group. Once an Obj is saved as a Source, "
    "the Obj is shielded in perpetuity from automatic database removal. "
    "If a Source is 'unsaved', its 'active' flag is set to False, but "
    "it is not purged."
)

Source.saved_by_id = sa.Column(
    sa.ForeignKey("users.id"),
    nullable=True,
    unique=False,
    index=True,
    doc="ID of the User that saved the Obj to its Group.",
)
Source.saved_by = relationship(
    "User",
    foreign_keys=[Source.saved_by_id],
    backref="saved_sources",
    doc="User that saved the Obj to its Group.",
)
Source.saved_at = sa.Column(
    sa.DateTime, nullable=True, doc="ISO UTC time when the Obj was saved to its Group."
)
Source.active = sa.Column(
    sa.Boolean,
    server_default="true",
    doc="Whether the Obj is still 'active' as a Source in its Group. "
    "If this flag is set to False, the Source will not appear in the Group's "
    "sample.",
)
Source.requested = sa.Column(
    sa.Boolean,
    server_default="false",
    doc="True if the source has been shared with another Group, but not saved "
    "by the recipient Group.",
)

Source.unsaved_by_id = sa.Column(
    sa.ForeignKey("users.id"),
    nullable=True,
    unique=False,
    index=True,
    doc="ID of the User who unsaved the Source.",
)
Source.unsaved_by = relationship(
    "User", foreign_keys=[Source.unsaved_by_id], doc="User who unsaved the Source."
)


def source_is_owned_by(self, user_or_token):
    """Return a boolean indicating whether the Source has been saved to
    any of a User or Token owner's accessible Groups.

    Parameters
    ----------
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.

    Returns
    -------
    owned : bool
       Whether the Candidate is owned by the User or Token owner.
    """

    source_group_ids = [
        row[0]
        for row in DBSession.query(Source.group_id)
        .filter(Source.obj_id == self.obj_id)
        .all()
    ]
    return bool(set(source_group_ids) & {g.id for g in user_or_token.accessible_groups})


def get_source_if_owned_by(obj_id, user_or_token, options=[]):
    """Return an Obj from the database if the Obj is a Source in at least
    one of the requesting User or Token owner's accessible Groups. If the Obj is not a
    Source in one of the User or Token owner's accessible Groups, raise an AccessError.
    If the Obj does not exist, return `None`.

    Parameters
    ----------
    obj_id : integer or string
       Primary key of the Obj.
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.
    options : list of `sqlalchemy.orm.MapperOption`s
       Options that wil be passed to `options()` in the loader query.

    Returns
    -------
    obj : `skyportal.models.Obj`
       The requested Obj.
    """

    if Source.query.filter(Source.obj_id == obj_id).first() is None:
        return None
    user_group_ids = [g.id for g in user_or_token.accessible_groups]
    s = (
        Source.query.filter(Source.obj_id == obj_id)
        .filter(Source.group_id.in_(user_group_ids))
        .options(options)
        .first()
    )
    if s is None:
        raise AccessError("Insufficient permissions.")
    return s.obj


Source.is_owned_by = source_is_owned_by
Source.get_obj_if_owned_by = get_source_if_owned_by


def get_obj_if_owned_by(obj_id, user_or_token, options=[]):
    """Return an Obj from the database if the Obj is either a Source or a Candidate in at least
    one of the requesting User or Token owner's accessible Groups. If the Obj is not a
    Source or a Candidate in one of the User or Token owner's accessible Groups, raise an AccessError.
    If the Obj does not exist, return `None`.

    Parameters
    ----------
    obj_id : integer or string
       Primary key of the Obj.
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.
    options : list of `sqlalchemy.orm.MapperOption`s
       Options that wil be passed to `options()` in the loader query.

    Returns
    -------
    obj : `skyportal.models.Obj`
       The requested Obj.
    """

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
    """Query the database and return the Comments on this Obj that are accessible
    to any of the User or Token owner's accessible Groups.

    Parameters
    ----------
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.

    Returns
    -------
    comment_list : list of `skyportal.models.Comment`
       The accessible comments attached to this Obj.
    """
    owned_comments = [
        comment for comment in self.comments if comment.is_owned_by(user_or_token)
    ]

    # Grab basic author info for the comments
    for comment in owned_comments:
        comment.author_info = comment.construct_author_info_dict()

    return owned_comments


Obj.get_comments_owned_by = get_obj_comments_owned_by


def get_obj_classifications_owned_by(self, user_or_token):
    """Query the database and return the Classifications on this Obj that are accessible
    to any of the User or Token owner's accessible Groups.

    Parameters
    ----------
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.

    Returns
    -------
    comment_list : list of `skyportal.models.Classification`
       The accessible classifications attached to this Obj.
    """
    return [
        classifications
        for classifications in self.classifications
        if classifications.is_owned_by(user_or_token)
    ]


Obj.get_classifications_owned_by = get_obj_classifications_owned_by


def get_photometry_owned_by_user(obj_id, user_or_token):
    """Query the database and return the Photometry for this Obj that is shared
    with any of the User or Token owner's accessible Groups.

    Parameters
    ----------
    obj_id : string
       The ID of the Obj to look up.
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.

    Returns
    -------
    photometry_list : list of `skyportal.models.Photometry`
       The accessible Photometry of this Obj.
    """
    return (
        Photometry.query.filter(Photometry.obj_id == obj_id)
        .filter(
            Photometry.groups.any(
                Group.id.in_([g.id for g in user_or_token.accessible_groups])
            )
        )
        .all()
    )


Obj.get_photometry_owned_by_user = get_photometry_owned_by_user


def get_spectra_owned_by(obj_id, user_or_token):
    """Query the database and return the Spectra for this Obj that are shared
    with any of the User or Token owner's accessible Groups.

    Parameters
    ----------
    obj_id : string
       The ID of the Obj to look up.
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.

    Returns
    -------
    photometry_list : list of `skyportal.models.Spectrum`
       The accessible Spectra of this Obj.
    """

    return (
        Spectrum.query.filter(Spectrum.obj_id == obj_id)
        .filter(
            Spectrum.groups.any(
                Group.id.in_([g.id for g in user_or_token.accessible_groups])
            )
        )
        .all()
    )


Obj.get_spectra_owned_by = get_spectra_owned_by


User.sources = relationship(
    'Obj',
    backref='users',
    secondary='join(Group, sources).join(group_users)',
    primaryjoin='group_users.c.user_id == users.c.id',
    passive_deletes=True,
    doc='The Sources accessible to this User.',
)


class SourceView(Base):
    """Record of an instance in which a Source was viewed via the frontend or
    retrieved via the API (for use in the "Top Sources" widget).
    """

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True,
        doc="Object ID for which the view was registered.",
    )
    username_or_token_id = sa.Column(
        sa.String,
        nullable=False,
        unique=False,
        doc="Username or token ID of the viewer.",
    )
    is_token = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether the viewer was a User or a Token.",
    )
    created_at = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="UTC timestamp of the view.",
    )


class Telescope(Base):
    """A ground or space-based observational facility that can host Instruments.
    """

    name = sa.Column(
        sa.String,
        unique=True,
        nullable=False,
        doc="Unabbreviated facility name (e.g., Palomar 200-inch Hale Telescope).",
    )
    nickname = sa.Column(
        sa.String, nullable=False, doc="Abbreviated facility name (e.g., P200)."
    )
    lat = sa.Column(sa.Float, nullable=True, doc='Latitude in deg.')
    lon = sa.Column(sa.Float, nullable=True, doc='Longitude in deg.')
    elevation = sa.Column(sa.Float, nullable=True, doc='Elevation in meters.')
    diameter = sa.Column(sa.Float, nullable=False, doc='Diameter in meters.')
    skycam_link = sa.Column(
        URLType, nullable=True, doc="Link to the telescope's sky camera."
    )
    robotic = sa.Column(
        sa.Boolean, default=False, nullable=False, doc="Is this telescope robotic?"
    )

    instruments = relationship(
        'Instrument',
        back_populates='telescope',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="The Instruments on this telescope.",
    )

    @property
    def observer(self):
        """Return an `astroplan.Observer` representing an observer at this
        facility, accounting for the latitude, longitude, elevation, and
        local time zone of the observatory (if ground based)."""
        tf = timezonefinder.TimezoneFinder()
        local_tz = tf.timezone_at(lng=self.lon, lat=self.lat)
        return astroplan.Observer(
            longitude=self.lon * u.deg,
            latitude=self.lat * u.deg,
            elevation=self.elevation * u.m,
            timezone=local_tz,
        )


class ArrayOfEnum(ARRAY):
    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)

    def result_processor(self, dialect, coltype):
        super_rp = super(ArrayOfEnum, self).result_processor(dialect, coltype)

        def handle_raw_string(value):
            if value is None or value == '{}':  # 2nd case, empty array
                return []
            inner = re.match(r"^{(.*)}$", value).group(1)
            return inner.split(",")

        def process(value):
            return super_rp(handle_raw_string(value))

        return process


ACL.created_by_instrument_id = sa.Column(
    sa.ForeignKey('instruments.id', ondelete='CASCADE'),
    nullable=True,
    index=True,
    doc="The ID of the instrument whose message listener created this token.",
)
ACL.created_by_instrument = relationship(
    'Instrument',
    back_populates='listener_tokens',
    doc="The instrument whose message listener created this token.",
)

Token.created_by_instrument_id = sa.Column(
    sa.ForeignKey('instruments.id', ondelete='CASCADE'),
    nullable=True,
    index=True,
    doc="The ID of the instrument whose message listener created this token.",
)
Token.created_by_instrument = relationship(
    'Instrument',
    back_populates='listener_tokens',
    doc="The instrument whose message listener created this token.",
)


class Instrument(Base):
    """An instrument attached to a telescope."""

    name = sa.Column(sa.String, unique=True, nullable=False, doc="Instrument name.")
    type = sa.Column(
        instrument_types,
        nullable=False,
        doc="Instrument type, one of Imager, Spectrograph, or Imaging Spectrograph.",
    )

    band = sa.Column(
        sa.String,
        doc="The spectral band covered by the instrument " "(e.g., Optical, IR).",
    )
    telescope_id = sa.Column(
        sa.ForeignKey('telescopes.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the Telescope that hosts the Instrument.",
    )
    telescope = relationship(
        'Telescope',
        back_populates='instruments',
        doc="The Telescope that hosts the Instrument.",
    )

    photometry = relationship(
        'Photometry',
        back_populates='instrument',
        doc="The Photometry produced by this instrument.",
    )
    spectra = relationship(
        'Spectrum',
        back_populates='instrument',
        doc="The Spectra produced by this instrument.",
    )

    # can be [] if an instrument is spec only
    filters = sa.Column(
        ArrayOfEnum(allowed_bandpasses),
        nullable=False,
        default=[],
        doc='List of filters on the instrument (if any).',
    )

    allocations = relationship(
        'Allocation',
        back_populates="instrument",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
    )
    observing_runs = relationship(
        'ObservingRun',
        back_populates='instrument',
        doc="List of ObservingRuns on the Instrument.",
    )

    api_classname = sa.Column(
        api_classnames, nullable=True, doc="Name of the instrument's API class."
    )

    listener_classname = sa.Column(
        listener_classnames,
        nullable=True,
        doc="Name of the instrument's listener class.",
    )

    listener_tokens = relationship(
        'Token',
        back_populates='created_by_instrument',
        doc="The active tokens associated with the instrument's request handler.",
    )

    listener_acl = relationship(
        'ACL',
        back_populates='created_by_instrument',
        doc="The ACL that remote facility tokens must possess to POST to this instrument's request handler.",
        uselist=False,
    )

    @property
    def does_spectroscopy(self):
        """Return a boolean indicating whether the instrument is capable of
        performing spectroscopy."""
        return 'spec' in self.type

    @property
    def does_imaging(self):
        """Return a boolean indicating whether the instrument is capable of
        performing imaging."""
        return 'imag' in self.type

    @property
    def api_class(self):
        return getattr(facility_apis, self.api_classname)

    def has_listener(self):
        return self.listener_classname is not None

    @property
    def listener_manager(instrument):
        if not instrument.has_listener():
            return None

        class ListenerManager:
            @staticmethod
            def clear_tokens():
                for token in instrument.listener_tokens:
                    DBSession().query(Token).filter(Token.id == token.id).delete()
                DBSession().commit()

            @staticmethod
            def create_or_get_acl():
                if instrument.listener_acl is None:
                    acl = ACL(f'Post to {instrument.name}')
                    DBSession().add(acl)
                    DBSession().commit()
                return instrument.listener_acl

            @staticmethod
            def new_token():
                token = Token(
                    created_by_instrument=instrument,
                    acls=[ListenerManager.create_or_get_acl()],
                )
                DBSession().add(token)
                DBSession().commit()
                return token

            @staticmethod
            def clear_acl():
                if instrument.listener_acl is not None:
                    DBSession().query(ACL).filter(
                        ACL.id == instrument.listener_acl.id
                    ).delete()
                DBSession().commit()

            @staticmethod
            def clear_tokens_and_acl():
                ListenerManager.clear_tokens()
                ListenerManager.clear_acl()

            @staticmethod
            def get_listener_class():
                user_class = getattr(facility_apis, instrument.listener_classname)
                class_with_auth_installed = ListenerManager.create_listener(user_class)
                return class_with_auth_installed

            @staticmethod
            def get_listener_endpoint():
                return requests.utils.quote(
                    f'/api/listener/{instrument.name}_{instrument.listener_classname}'
                )

            @staticmethod
            def create_listener(user_class):
                if user_class.enable_token_authentication:
                    if instrument.listener_tokens is None:
                        ListenerManager.new_token()

                    class ObservatoryResponseHandler(user_class):
                        @permissions([instrument.listener_acl])
                        def post(self):
                            super().post()

                else:
                    ObservatoryResponseHandler = user_class
                return ObservatoryResponseHandler

        return ListenerManager


class Allocation(Base):
    """An allocation of observing time on a robotic instrument."""

    pi = sa.Column(sa.String, doc="The PI of the allocation's proposal.")
    proposal_id = sa.Column(
        sa.String, doc="The ID of the proposal associated with this allocation."
    )
    start_date = sa.Column(sa.DateTime, doc='The UTC start date of the allocation.')
    end_date = sa.Column(sa.DateTime, doc='The UTC end date of the allocation.')
    hours_allocated = sa.Column(
        sa.Float, nullable=False, doc='The number of hours allocated.'
    )
    requests = relationship(
        'FollowupRequest',
        back_populates='allocation',
        doc='The requests made against this allocation.',
    )

    group_id = sa.Column(
        sa.ForeignKey('groups.id', ondelete='CASCADE'),
        index=True,
        doc='The ID of the Group the allocation is associated with.',
        nullable=False,
    )
    group = relationship(
        'Group',
        back_populates='allocations',
        doc='The Group the allocation is associated with.',
    )

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        index=True,
        doc="The ID of the Instrument the allocation is associated with.",
        nullable=False,
    )
    instrument = relationship(
        'Instrument',
        back_populates='allocations',
        doc="The Instrument the allocation is associated with.",
    )


class Taxonomy(Base):
    """An ontology within which Objs can be classified."""

    __tablename__ = 'taxonomies'
    name = sa.Column(
        sa.String,
        nullable=False,
        doc='Short string to make this taxonomy memorable to end users.',
    )
    hierarchy = sa.Column(
        JSONB,
        nullable=False,
        doc='Nested JSON describing the taxonomy '
        'which should be validated against '
        'a schema before entry.',
    )
    provenance = sa.Column(
        sa.String,
        nullable=True,
        doc='Identifier (e.g., URL or git hash) that '
        'uniquely ties this taxonomy back '
        'to an origin or place of record.',
    )
    version = sa.Column(
        sa.String, nullable=False, doc='Semantic version of this taxonomy'
    )

    isLatest = sa.Column(
        sa.Boolean,
        default=True,
        nullable=False,
        doc='Consider this the latest version of '
        'the taxonomy with this name? Defaults '
        'to True.',
    )
    groups = relationship(
        "Group",
        secondary="group_taxonomy",
        cascade="save-update," "merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="List of Groups that have access to this Taxonomy.",
    )

    classifications = relationship(
        'Classification',
        back_populates='taxonomy',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        order_by="Classification.created_at",
        doc="Classifications made within this Taxonomy.",
    )


GroupTaxonomy = join_model("group_taxonomy", Group, Taxonomy)
GroupTaxonomy.__doc__ = "Join table mapping Groups to Taxonomies."


def get_taxonomy_usable_by_user(taxonomy_id, user_or_token):
    """Query the database and return the requested Taxonomy if it is accessible
    to the requesting User or Token owner. If the Taxonomy is not accessible or
    if it does not exist, return `None`.

    Parameters
    ----------
    taxonomy_id : integer
       The ID of the requested Taxonomy.
    user_or_token : `baselayer.app.models.User` or `baselayer.app.models.Token`
       The requesting `User` or `Token` object.

    Returns
    -------
    tax : `skyportal.models.Taxonomy`
       The requested Taxonomy.
    """

    return (
        Taxonomy.query.filter(Taxonomy.id == taxonomy_id)
        .filter(Taxonomy.groups.any(Group.id.in_([g.id for g in user_or_token.groups])))
        .all()
    )


Taxonomy.get_taxonomy_usable_by_user = get_taxonomy_usable_by_user


class Comment(Base):
    """A comment made by a User or a Robot (via the API) on a Source."""

    text = sa.Column(sa.String, nullable=False, doc="Comment body.")
    ctype = sa.Column(
        sa.Enum('text', 'redshift', name='comment_types', validate_strings=True),
        doc="Comment type. Can be one of 'text' or 'redshift'.",
    )

    attachment_name = sa.Column(
        sa.String, nullable=True, doc="Filename of the attachment."
    )
    attachment_type = sa.Column(
        sa.String, nullable=True, doc="Attachment extension, (e.g., pdf, png)."
    )
    attachment_bytes = sa.Column(
        sa.types.LargeBinary,
        nullable=True,
        doc="Binary representation of the attachment.",
    )

    origin = sa.Column(sa.String, nullable=True, doc='Comment origin.')
    author = relationship(
        "User", back_populates="comments", doc="Comment's author.", uselist=False,
    )
    author_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Comment author's User instance.",
    )
    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Comment's Obj.",
    )
    obj = relationship('Obj', back_populates='comments', doc="The Comment's Obj.")
    groups = relationship(
        "Group",
        secondary="group_comments",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can see the comment.",
    )

    def construct_author_info_dict(self):
        return {
            field: getattr(self.author, field)
            for field in ('username', 'first_name', 'last_name', 'gravatar_url')
        }

    @classmethod
    def get_if_owned_by(cls, ident, user, options=[]):
        comment = cls.query.options(options).get(ident)

        if comment is not None and not comment.is_owned_by(user):
            raise AccessError('Insufficient permissions.')

        # Grab basic author info for the comment
        comment.author_info = comment.construct_author_info_dict()

        return comment


GroupComment = join_model("group_comments", Group, Comment)
GroupComment.__doc__ = "Join table mapping Groups to Comments."

User.comments = relationship("Comment", back_populates="author")


class Classification(Base):
    """Classification of an Obj."""

    classification = sa.Column(sa.String, nullable=False, doc="The assigned class.")
    taxonomy_id = sa.Column(
        sa.ForeignKey('taxonomies.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Taxonomy in which this Classification was made.",
    )
    taxonomy = relationship(
        'Taxonomy',
        back_populates='classifications',
        doc="Taxonomy in which this Classification was made.",
    )
    probability = sa.Column(
        sa.Float,
        doc='User-assigned probability of belonging to this class',
        nullable=True,
    )

    author_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User that made this Classification",
    )
    author = relationship('User', doc="The User that made this classification.")
    author_name = sa.Column(
        sa.String,
        nullable=False,
        doc="User.username or Token.id " "of the Classification's author.",
    )
    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Classification's Obj.",
    )
    obj = relationship(
        'Obj', back_populates='classifications', doc="The Classification's Obj."
    )
    groups = relationship(
        "Group",
        secondary="group_classifications",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can access this Classification.",
    )


GroupClassifications = join_model("group_classifications", Group, Classification)
GroupClassifications.__doc__ = "Join table mapping Groups to Classifications."


class Photometry(Base, ha.Point):
    """Calibrated measurement of the flux of an object through a broadband filter."""

    __tablename__ = 'photometry'
    mjd = sa.Column(sa.Float, nullable=False, doc='MJD of the observation.')
    flux = sa.Column(
        sa.Float,
        doc='Flux of the observation in µJy. '
        'Corresponds to an AB Zeropoint of 23.9 in all '
        'filters.',
    )
    fluxerr = sa.Column(
        sa.Float, nullable=False, doc='Gaussian error on the flux in µJy.'
    )
    filter = sa.Column(
        allowed_bandpasses,
        nullable=False,
        doc='Filter with which the observation was taken.',
    )

    ra_unc = sa.Column(sa.Float, doc="Uncertainty of ra position [arcsec]")
    dec_unc = sa.Column(sa.Float, doc="Uncertainty of dec position [arcsec]")

    original_user_data = sa.Column(
        JSONB,
        doc='Original data passed by the user '
        'through the PhotometryHandler.POST '
        'API or the PhotometryHandler.PUT '
        'API. The schema of this JSON '
        'validates under either '
        'schema.PhotometryFlux or schema.PhotometryMag '
        '(depending on how the data was passed).',
    )
    altdata = sa.Column(JSONB, doc="Arbitrary metadata in JSON format..")
    upload_id = sa.Column(
        sa.String,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        doc="ID of the batch in which this Photometry was uploaded (for bulk deletes).",
    )
    alert_id = sa.Column(
        sa.BigInteger,
        nullable=True,
        unique=True,
        doc="ID of the alert from which this Photometry was extracted (if any).",
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Photometry's Obj.",
    )
    obj = relationship('Obj', back_populates='photometry', doc="The Photometry's Obj.")
    groups = relationship(
        "Group",
        secondary="group_photometry",
        back_populates="photometry",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can access this Photometry.",
    )
    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id'),
        nullable=False,
        index=True,
        doc="ID of the Instrument that took this Photometry.",
    )
    instrument = relationship(
        'Instrument',
        back_populates='photometry',
        doc="Instrument that took this Photometry.",
    )
    thumbnails = relationship(
        'Thumbnail', passive_deletes=True, doc="Thumbnails for this Photometry."
    )

    followup_request_id = sa.Column(
        sa.ForeignKey('followuprequests.id'), nullable=True, index=True
    )
    followup_request = relationship('FollowupRequest', back_populates='photometry')

    assignment_id = sa.Column(
        sa.ForeignKey('classicalassignments.id'), nullable=True, index=True
    )
    assignment = relationship('ClassicalAssignment', back_populates='photometry')

    @hybrid_property
    def mag(self):
        """The magnitude of the photometry point in the AB system."""
        if self.flux is not None and self.flux > 0:
            return -2.5 * np.log10(self.flux) + PHOT_ZP
        else:
            return None

    @hybrid_property
    def e_mag(self):
        """The error on the magnitude of the photometry point."""
        if self.flux is not None and self.flux > 0 and self.fluxerr > 0:
            return (2.5 / np.log(10)) * (self.fluxerr / self.flux)
        else:
            return None

    @mag.expression
    def mag(cls):
        """The magnitude of the photometry point in the AB system."""
        return sa.case(
            [
                (
                    sa.and_(cls.flux != None, cls.flux > 0),  # noqa
                    -2.5 * sa.func.log(cls.flux) + PHOT_ZP,
                )
            ],
            else_=None,
        )

    @e_mag.expression
    def e_mag(cls):
        """The error on the magnitude of the photometry point."""
        return sa.case(
            [
                (
                    sa.and_(
                        cls.flux != None, cls.flux > 0, cls.fluxerr > 0
                    ),  # noqa: E711
                    2.5 / sa.func.ln(10) * cls.fluxerr / cls.flux,
                )
            ],
            else_=None,
        )

    @hybrid_property
    def jd(self):
        """Julian Date of the exposure that produced this Photometry."""
        return self.mjd + 2_400_000.5

    @hybrid_property
    def iso(self):
        """UTC ISO timestamp (ArrowType) of the exposure that produced this Photometry."""
        return arrow.get((self.mjd - 40_587) * 86400.0)

    @iso.expression
    def iso(cls):
        """UTC ISO timestamp (ArrowType) of the exposure that produced this Photometry."""
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd - 40_587) * 86400.0)

    @hybrid_property
    def snr(self):
        """Signal-to-noise ratio of this Photometry point."""
        return self.flux / self.fluxerr if self.flux and self.fluxerr else None

    @snr.expression
    def snr(self):
        """Signal-to-noise ratio of this Photometry point."""
        return self.flux / self.fluxerr


GroupPhotometry = join_model("group_photometry", Group, Photometry)
GroupPhotometry.__doc__ = "Join table mapping Groups to Photometry."


class Spectrum(Base):
    """Wavelength-dependent measurement of the flux of an object through a
    dispersive element."""

    __tablename__ = 'spectra'
    # TODO better numpy integration
    wavelengths = sa.Column(
        NumpyArray, nullable=False, doc="Wavelengths of the spectrum [Angstrom]."
    )
    fluxes = sa.Column(
        NumpyArray,
        nullable=False,
        doc="Flux of the Spectrum [F_lambda, arbitrary units].",
    )
    errors = sa.Column(
        NumpyArray,
        doc="Errors on the fluxes of the spectrum [F_lambda, same units as `fluxes`.]",
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of this Spectrum's Obj.",
    )
    obj = relationship('Obj', back_populates='spectra', doc="The Spectrum's Obj.")
    observed_at = sa.Column(
        sa.DateTime,
        nullable=False,
        doc="Median UTC ISO time stamp of the exposure or exposures in which the Spectrum was acquired.",
    )
    origin = sa.Column(sa.String, nullable=True, doc="Origin of the spectrum.")
    # TODO program?
    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Instrument that acquired the Spectrum.",
    )
    instrument = relationship(
        'Instrument',
        back_populates='spectra',
        doc="The Instrument that acquired the Spectrum.",
    )
    groups = relationship(
        "Group",
        secondary="group_spectra",
        back_populates="spectra",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='Groups that can view this spectrum.',
    )

    followup_request_id = sa.Column(sa.ForeignKey('followuprequests.id'), nullable=True)
    followup_request = relationship('FollowupRequest', back_populates='spectra')

    assignment_id = sa.Column(sa.ForeignKey('classicalassignments.id'), nullable=True)
    assignment = relationship('ClassicalAssignment', back_populates='spectra')

    @classmethod
    def from_ascii(cls, filename, obj_id, instrument_id, observed_at):
        """Generate a `Spectrum` from an ascii file.

        Parameters
        ----------

        filename : str
           The name of the ASCII file containing the spectrum.
        obj_id : str
           The name of the Spectrum's Obj.
        instrument_id : int
           ID of the Instrument with which this Spectrum was acquired.
        observed_at : string or datetime
           Median UTC ISO time stamp of the exposure or exposures in which the Spectrum was acquired."

        Returns
        -------

        spec : `skyportal.models.Spectrum`
           The Spectrum generated from the ASCII file.

        """
        data = np.loadtxt(filename)
        if data.shape[1] != 2:  # TODO support other formats
            raise ValueError(f"Expected 2 columns, got {data.shape[1]}")

        return cls(
            wavelengths=data[:, 0],
            fluxes=data[:, 1],
            obj_id=obj_id,
            instrument_id=instrument_id,
            observed_at=observed_at,
        )


GroupSpectrum = join_model("group_spectra", Group, Spectrum)
GroupSpectrum.__doc__ = 'Join table mapping Groups to Spectra.'


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
    """A request for follow-up data (spectroscopy, photometry, or both) using a
    robotic instrument."""

    requester = relationship(
        User,
        back_populates='followup_requests',
        doc="The User who requested the follow-up.",
    )
    requester_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User who requested the follow-up.",
    )
    obj = relationship('Obj', back_populates='followup_requests', doc="The target Obj.")
    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the target Obj.",
    )

    payload = sa.Column(
        psql.JSONB, nullable=True, doc="Content of the followup request."
    )
    status = sa.Column(sa.String(), nullable=False, default="pending submission")

    allocation_id = sa.Column(
        sa.ForeignKey('allocations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    allocation = relationship('Allocation', back_populates='requests')

    http_requests = relationship(
        'FollowupRequestHTTPRequest',
        back_populates='request',
        order_by="FollowupRequestHTTPRequest.created_at.desc()",
    )

    photometry = relationship('Photometry', back_populates='followup_request')
    spectra = relationship('Spectrum', back_populates='followup_request')

    @property
    def instrument(self):
        return self.allocation.instrument

    def is_owned_by(self, user_or_token):
        """Return a boolean indicating whether a FollowupRequest belongs to
        an allocation that is accessible to the given user or token.

        Parameters
        ----------
        user_or_token: `baselayer.app.models.User` or `baselayer.app.models.Token`
           The User or Token to check.

        Returns
        -------
        owned: bool
           Whether the FollowupRequest belongs to an Allocation that is
           accessible to the given user or token.
        """

        user_or_token_group_ids = [g.id for g in user_or_token.accessible_groups]
        return self.allocation.group_id in user_or_token_group_ids


class FollowupRequestHTTPRequest(Base):

    created_at = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="UTC time this FollowupRequestHTTPRequest was created.",
    )
    content = sa.Column(sa.Text, doc="The content of the request.", nullable=False)

    request_id = sa.Column(
        sa.ForeignKey('followuprequests.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
        doc="The ID of the FollowupRequest this message pertains to.",
    )

    request = relationship(
        'FollowupRequest',
        back_populates='http_requests',
        doc="The FollowupRequest this message pertains to.",
    )
    origin = sa.Column(
        followup_http_request_origins, doc='Origin of the HTTP request.', nullable=False
    )


User.followup_requests = relationship(
    'FollowupRequest',
    back_populates='requester',
    doc="The follow-up requests this User has made.",
)


class Thumbnail(Base):
    """Thumbnail image centered on the location of an Obj."""

    # TODO delete file after deleting row
    type = sa.Column(
        thumbnail_types, doc='Thumbnail type (e.g., ref, new, sub, dr8, ...)'
    )
    file_uri = sa.Column(
        sa.String(),
        nullable=True,
        index=False,
        unique=False,
        doc="Path of the Thumbnail on the machine running SkyPortal.",
    )
    public_url = sa.Column(
        sa.String(),
        nullable=True,
        index=False,
        unique=False,
        doc="Publically accessible URL of the thumbnail.",
    )
    origin = sa.Column(sa.String, nullable=True, doc="Origin of the Thumbnail.")
    photometry_id = sa.Column(
        sa.ForeignKey('photometry.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Thumbnail's corresponding Photometry point.",
    )
    photometry = relationship(
        'Photometry',
        back_populates='thumbnails',
        doc="The Thumbnail's corresponding Photometry point.",
    )
    obj = relationship(
        'Obj',
        back_populates='thumbnails',
        uselist=False,
        secondary='photometry',
        passive_deletes=True,
        doc="The Thumbnail's Obj.",
    )


class ObservingRun(Base):
    """A classical observing run with a target list (of Objs)."""

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Instrument used for this run.",
    )
    instrument = relationship(
        'Instrument',
        cascade='save-update, merge, refresh-expire, expunge',
        uselist=False,
        back_populates='observing_runs',
        doc="The Instrument for this run.",
    )

    # name of the PI
    pi = sa.Column(sa.String, doc="The name(s) of the PI(s) of this run.")
    observers = sa.Column(sa.String, doc="The name(s) of the observer(s) on this run.")

    sources = relationship(
        'Obj',
        secondary='join(ClassicalAssignment, Obj)',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="The targets [Objs] for this run.",
    )

    # let this be nullable to accommodate external groups' runs
    group = relationship(
        'Group',
        back_populates='observing_runs',
        doc='The Group associated with this Run.',
    )
    group_id = sa.Column(
        sa.ForeignKey('groups.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        doc='The ID of the Group associated with this run.',
    )

    # the person who uploaded the run
    owner = relationship(
        'User',
        back_populates='observing_runs',
        doc="The User who created this ObservingRun.",
    )
    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this ObservingRun.",
    )

    assignments = relationship(
        'ClassicalAssignment',
        passive_deletes=True,
        doc="The Target Assignments for this Run.",
    )
    calendar_date = sa.Column(
        sa.Date, nullable=False, index=True, doc="The Local Calendar date of this Run."
    )

    @property
    def _calendar_noon(self):
        observer = self.instrument.telescope.observer
        year = self.calendar_date.year
        month = self.calendar_date.month
        day = self.calendar_date.day
        hour = 12
        noon = datetime(
            year=year, month=month, day=day, hour=hour, tzinfo=observer.timezone
        )
        noon = noon.astimezone(timezone.utc).timestamp()
        noon = ap_time.Time(noon, format='unix')
        return noon

    @property
    def sunset(self):
        """The UTC timestamp of Sunset on this run."""
        return self.instrument.telescope.observer.sun_set_time(
            self._calendar_noon, which='next'
        )

    @property
    def sunrise(self):
        """The UTC timestamp of Sunrise on this run."""
        return self.instrument.telescope.observer.sun_rise_time(
            self._calendar_noon, which='next'
        )

    @property
    def twilight_evening_nautical(self):
        """The UTC timestamp of evening nautical (-12 degree) twilight on this run."""
        return self.instrument.telescope.observer.twilight_evening_nautical(
            self._calendar_noon, which='next'
        )

    @property
    def twilight_morning_nautical(self):
        """The UTC timestamp of morning nautical (-12 degree) twilight on this run."""
        return self.instrument.telescope.observer.twilight_morning_nautical(
            self._calendar_noon, which='next'
        )

    @property
    def twilight_evening_astronomical(self):
        """The UTC timestamp of evening astronomical (-18 degree) twilight on this run."""
        return self.instrument.telescope.observer.twilight_evening_astronomical(
            self._calendar_noon, which='next'
        )

    @property
    def twilight_morning_astronomical(self):
        """The UTC timestamp of morning astronomical (-18 degree) twilight on this run."""
        return self.instrument.telescope.observer.twilight_morning_astronomical(
            self._calendar_noon, which='next'
        )


User.observing_runs = relationship(
    'ObservingRun',
    cascade='save-update, merge, refresh-expire, expunge',
    doc="Observing Runs this User has created.",
)


class ClassicalAssignment(Base):
    """Assignment of an Obj to an Observing Run as a target."""

    requester_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The ID of the User who created this assignment.",
    )
    requester = relationship(
        "User",
        back_populates="assignments",
        foreign_keys=[requester_id],
        doc="The User who created this assignment.",
    )

    last_modified_by_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_id])

    obj = relationship('Obj', back_populates='assignments', doc='The assigned Obj.')
    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc='ID of the assigned Obj.',
    )

    comment = sa.Column(
        sa.String(),
        doc="A comment on the assignment. "
        "Typically a justification for the request, "
        "or instructions for taking the data.",
    )
    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending",
        doc='Status of the assignment [done, not done, pending].',
    )
    priority = sa.Column(
        followup_priorities,
        nullable=False,
        doc='Priority of the request (1 = lowest, 5 = highest).',
    )
    spectra = relationship(
        "Spectrum",
        back_populates="assignment",
        doc="Spectra produced by the assignment.",
    )
    photometry = relationship(
        "Photometry",
        back_populates="assignment",
        doc="Photometry produced by the assignment.",
    )

    run = relationship(
        'ObservingRun',
        back_populates='assignments',
        doc="The ObservingRun this target was assigned to.",
    )
    run_id = sa.Column(
        sa.ForeignKey('observingruns.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the ObservingRun this target was assigned to.",
    )

    @hybrid_property
    def instrument(self):
        """The instrument in use on the assigned ObservingRun."""
        return self.run.instrument

    @property
    def rise_time(self):
        """The UTC time at which the object rises on this run."""
        observer = self.instrument.telescope.observer
        target = self.obj.target
        return observer.target_rise_time(
            self.run.sunset, target, which='next', horizon=30 * u.degree
        )

    @property
    def set_time(self):
        """The UTC time at which the object sets on this run."""
        observer = self.instrument.telescope.observer
        target = self.obj.target
        return observer.target_set_time(
            self.rise_time, target, which='next', horizon=30 * u.degree
        )


User.assignments = relationship(
    'ClassicalAssignment',
    back_populates='requester',
    doc="Objs the User has assigned to ObservingRuns.",
    foreign_keys="ClassicalAssignment.requester_id",
)


class Invitation(Base):
    token = sa.Column(sa.String(), nullable=False, unique=True)
    groups = relationship(
        "Group",
        secondary="group_invitations",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
    )
    admin_for_groups = sa.Column(psql.ARRAY(sa.Boolean), nullable=False)
    user_email = sa.Column(EmailType(), nullable=True)
    invited_by = relationship(
        "User",
        secondary="user_invitations",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        uselist=False,
    )
    used = sa.Column(sa.Boolean, nullable=False, default=False)


GroupInvitation = join_model('group_invitations', Group, Invitation)
UserInvitation = join_model("user_invitations", User, Invitation)


@event.listens_for(Invitation, 'after_insert')
def send_user_invite_email(mapper, connection, target):
    _, cfg = load_env()
    ports_to_ignore = {True: 443, False: 80}  # True/False <-> server.ssl=True/False
    app_base_url = (
        f"{'https' if cfg['server.ssl'] else 'http'}:"
        f"//{cfg['server.host']}"
        + (
            f":{cfg['server.port']}"
            if (
                cfg["server.port"] is not None
                and cfg["server.port"] != ports_to_ignore[cfg["server.ssl"]]
            )
            else ""
        )
    )
    link_location = f'{app_base_url}/login/google-oauth2/?invite_token={target.token}'
    message = Mail(
        from_email=cfg["invitations.from_email"],
        to_emails=target.user_email,
        subject=cfg["invitations.email_subject"],
        html_content=(
            f'{cfg["invitations.email_body_preamble"]}<br /><br />'
            f'Please click <a href="{link_location}">here</a> to join.'
        ),
    )
    sg = SendGridAPIClient(cfg["invitations.sendgrid_api_key"])
    sg.send(message)


schema.setup_schema()
