__all__ = ['Obj']

import uuid
import requests
import re
import os

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_method

from astropy import coordinates as ap_coord
from astropy import units as u
import astroplan
import conesearch_alchemy
import healpix_alchemy
import numpy as np

from baselayer.app.env import load_env
from baselayer.app.models import (
    Base,
    DBSession,
    public,
    restricted,
    CustomUserAccessControl,
)
from baselayer.log import make_log

from .photometry import Photometry
from .spectrum import Spectrum
from .candidate import Candidate
from .thumbnail import Thumbnail
from .cosmo import cosmo

_, cfg = load_env()
log = make_log('models.obj')

# The minimum signal-to-noise ratio to consider a photometry point as a detection
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]

PS1_CUTOUT_TIMEOUT = 10


def delete_obj_if_all_data_owned(cls, user_or_token):
    from .source import Source

    allow_nonadmins = cfg["misc.allow_nonadmins_delete_objs"] or False

    deletable_photometry = Photometry.query_records_accessible_by(
        user_or_token, mode="delete"
    ).subquery()
    nondeletable_photometry = (
        DBSession()
        .query(Photometry.obj_id)
        .join(
            deletable_photometry,
            deletable_photometry.c.id == Photometry.id,
            isouter=True,
        )
        .filter(deletable_photometry.c.id.is_(None))
        .distinct(Photometry.obj_id)
        .subquery()
    )

    deletable_spectra = Spectrum.query_records_accessible_by(
        user_or_token, mode="delete"
    ).subquery()
    nondeletable_spectra = (
        DBSession()
        .query(Spectrum.obj_id)
        .join(
            deletable_spectra,
            deletable_spectra.c.id == Spectrum.id,
            isouter=True,
        )
        .filter(deletable_spectra.c.id.is_(None))
        .distinct(Spectrum.obj_id)
        .subquery()
    )

    deletable_candidates = Candidate.query_records_accessible_by(
        user_or_token, mode="delete"
    ).subquery()
    nondeletable_candidates = (
        DBSession()
        .query(Candidate.obj_id)
        .join(
            deletable_candidates,
            deletable_candidates.c.id == Candidate.id,
            isouter=True,
        )
        .filter(deletable_candidates.c.id.is_(None))
        .distinct(Candidate.obj_id)
        .subquery()
    )

    deletable_sources = Source.query_records_accessible_by(
        user_or_token, mode="delete"
    ).subquery()
    nondeletable_sources = (
        DBSession()
        .query(Source.obj_id)
        .join(
            deletable_sources,
            deletable_sources.c.id == Source.id,
            isouter=True,
        )
        .filter(deletable_sources.c.id.is_(None))
        .distinct(Source.obj_id)
        .subquery()
    )

    return (
        DBSession()
        .query(cls)
        .join(
            nondeletable_photometry,
            nondeletable_photometry.c.obj_id == cls.id,
            isouter=True,
        )
        .filter(nondeletable_photometry.c.obj_id.is_(None))
        .join(
            nondeletable_spectra,
            nondeletable_spectra.c.obj_id == cls.id,
            isouter=True,
        )
        .filter(nondeletable_spectra.c.obj_id.is_(None))
        .join(
            nondeletable_candidates,
            nondeletable_candidates.c.obj_id == cls.id,
            isouter=True,
        )
        .filter(nondeletable_candidates.c.obj_id.is_(None))
        .join(
            nondeletable_sources,
            nondeletable_sources.c.obj_id == cls.id,
            isouter=True,
        )
        .filter(nondeletable_sources.c.obj_id.is_(None))
        .filter(sa.literal(allow_nonadmins))
    )


class Obj(Base, conesearch_alchemy.Point):
    """A record of an astronomical Object and its metadata, such as position,
    positional uncertainties, name, and redshift."""

    update = public
    delete = restricted | CustomUserAccessControl(delete_obj_if_all_data_owned)

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
    redshift = sa.Column(sa.Float, nullable=True, index=True, doc="Redshift.")
    redshift_error = sa.Column(sa.Float, nullable=True, doc="Redshift error.")
    redshift_origin = sa.Column(sa.String, nullable=True, doc="Redshift source.")
    redshift_history = sa.Column(
        JSONB,
        nullable=True,
        doc="Record of who set which redshift values and when.",
    )
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
    alias = sa.Column(
        sa.ARRAY(sa.String), nullable=True, doc="Alternative names for this object."
    )

    healpix = sa.Column(healpix_alchemy.Point, index=True)

    internal_key = sa.Column(
        sa.String,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        doc="Internal key used for secure websocket messaging.",
    )

    candidates = relationship(
        'Candidate',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="Candidate.passed_at",
        doc="Candidates associated with the object.",
    )

    comments = relationship(
        'Comment',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="Comment.created_at",
        doc="Comments posted about the object.",
    )

    comments_on_spectra = relationship(
        'CommentOnSpectrum',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="CommentOnSpectrum.created_at",
        doc="Comments posted about spectra belonging to the object.",
    )

    annotations = relationship(
        'Annotation',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        order_by="Annotation.created_at",
        doc="Auto-annotations posted about the object.",
    )

    annotations_on_spectra = relationship(
        'AnnotationOnSpectrum',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="AnnotationOnSpectrum.created_at",
        doc="Auto-annotations posted about a spectrum belonging to the object.",
    )

    classifications = relationship(
        'Classification',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete-orphan, delete',
        passive_deletes=True,
        order_by="Classification.created_at",
        doc="Classifications of the object.",
    )

    photometry = relationship(
        'Photometry',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        single_parent=True,
        passive_deletes=True,
        order_by="Photometry.mjd",
        doc="Photometry of the object.",
    )

    detect_photometry_count = sa.Column(
        sa.Integer,
        nullable=True,
        doc="How many times the object was detected above :math:`S/N = phot_detection_threshold (3.0 by default)`.",
    )

    spectra = relationship(
        'Spectrum',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        single_parent=True,
        passive_deletes=True,
        order_by="Spectrum.observed_at",
        doc="Spectra of the object.",
    )
    thumbnails = relationship(
        'Thumbnail',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="Thumbnails of the object.",
    )

    followup_requests = relationship(
        'FollowupRequest',
        back_populates='obj',
        cascade='delete',
        passive_deletes=True,
        doc="Robotic follow-up requests of the object.",
    )
    assignments = relationship(
        'ClassicalAssignment',
        back_populates='obj',
        cascade='delete',
        passive_deletes=True,
        doc="Assignments of the object to classical observing runs.",
    )

    obj_notifications = relationship(
        "SourceNotification",
        back_populates="source",
        cascade='delete',
        passive_deletes=True,
        doc="Notifications regarding the object sent out by users",
    )

    @hybrid_method
    def last_detected_at(self, user):
        """UTC ISO date at which the object was last detected above a given S/N (3.0 by default)."""
        detections = [
            phot.iso
            for phot in Photometry.query_records_accessible_by(user)
            .filter(Photometry.obj_id == self.id)
            .all()
            if phot.snr is not None and phot.snr > PHOT_DETECTION_THRESHOLD
        ]
        return max(detections) if detections else None

    @last_detected_at.expression
    def last_detected_at(cls, user):
        """UTC ISO date at which the object was last detected above a given S/N (3.0 by default)."""
        return (
            Photometry.query_records_accessible_by(
                user, columns=[sa.func.max(Photometry.iso)], mode="read"
            )
            .filter(Photometry.obj_id == cls.id)
            .filter(Photometry.snr.isnot(None))
            .filter(Photometry.snr > PHOT_DETECTION_THRESHOLD)
            .label('last_detected_at')
        )

    @hybrid_method
    def last_detected_mag(self, user):
        """Magnitude at which the object was last detected above a given S/N (3.0 by default)."""
        return (
            Photometry.query_records_accessible_by(
                user, columns=[Photometry.mag], mode="read"
            )
            .filter(Photometry.obj_id == self.id)
            .filter(Photometry.snr.isnot(None))
            .filter(Photometry.snr > PHOT_DETECTION_THRESHOLD)
            .order_by(Photometry.mjd.desc())
            .limit(1)
            .scalar()
        )

    @last_detected_mag.expression
    def last_detected_mag(cls, user):
        """Magnitude at which the object was last detected above a given S/N (3.0 by default)."""
        return (
            Photometry.query_records_accessible_by(
                user, columns=[Photometry.mag], mode="read"
            )
            .filter(Photometry.obj_id == cls.id)
            .filter(Photometry.snr.isnot(None))
            .filter(Photometry.snr > PHOT_DETECTION_THRESHOLD)
            .order_by(Photometry.mjd.desc())
            .limit(1)
            .label('last_detected_mag')
        )

    @hybrid_method
    def peak_detected_at(self, user):
        """UTC ISO date at which the object was detected at peak magnitude above a given S/N (3.0 by default)."""
        detections = [
            (phot.iso, phot.mag)
            for phot in Photometry.query_records_accessible_by(user)
            .filter(Photometry.obj_id == self.id)
            .all()
            if phot.snr is not None and phot.snr > PHOT_DETECTION_THRESHOLD
        ]
        return max(detections, key=(lambda x: x[1]))[0] if detections else None

    @peak_detected_at.expression
    def peak_detected_at(cls, user):
        """UTC ISO date at which the object was detected at peak magnitude above a given S/N (3.0 by default)."""
        return (
            Photometry.query_records_accessible_by(
                user, columns=[Photometry.iso], mode="read"
            )
            .filter(Photometry.obj_id == cls.id)
            .filter(Photometry.snr.isnot(None))
            .filter(Photometry.snr > PHOT_DETECTION_THRESHOLD)
            .order_by(Photometry.mag.desc())
            .limit(1)
            .label('peak_detected_at')
        )

    @hybrid_method
    def peak_detected_mag(self, user):
        """Peak magnitude at which the object was detected above a given S/N (3.0 by default)."""
        return (
            Photometry.query_records_accessible_by(
                user, columns=[sa.func.max(Photometry.mag)], mode="read"
            )
            .filter(Photometry.obj_id == self.id)
            .filter(Photometry.snr.isnot(None))
            .filter(Photometry.snr > PHOT_DETECTION_THRESHOLD)
            .scalar()
        )

    @peak_detected_mag.expression
    def peak_detected_mag(cls, user):
        """Peak magnitude at which the object was detected above a given S/N (3.0 by default)."""
        return (
            Photometry.query_records_accessible_by(
                user, columns=[sa.func.max(Photometry.mag)], mode="read"
            )
            .filter(Photometry.obj_id == cls.id)
            .filter(Photometry.snr.isnot(None))
            .filter(Photometry.snr > PHOT_DETECTION_THRESHOLD)
            .label('peak_detected_mag')
        )

    def add_linked_thumbnails(self, session=DBSession):
        """Determine the URLs of the SDSS and DESI DR8 thumbnails of the object,
        insert them into the Thumbnails table, and link them to the object."""
        sdss_thumb = Thumbnail(obj=self, public_url=self.sdss_url, type='sdss')
        dr8_thumb = Thumbnail(obj=self, public_url=self.desi_dr8_url, type='dr8')
        session.add_all([sdss_thumb, dr8_thumb])
        session.commit()

    def add_ps1_thumbnail(self, session=DBSession):
        ps1_thumb = Thumbnail(obj=self, public_url=self.panstarrs_url, type="ps1")
        session.add(ps1_thumb)
        session.commit()

    @property
    def sdss_url(self):
        """Construct URL for public Sloan Digital Sky Survey (SDSS) cutout."""
        return (
            f"https://skyserver.sdss.org/dr12/SkyserverWS/ImgCutout/getjpeg"
            f"?ra={self.ra}&dec={self.dec}&scale=0.3&width=200&height=200"
            f"&opt=G&query=&Grid=on"
        )

    @property
    def desi_dr8_url(self):
        """Construct URL for public DESI DR8 cutout."""
        return (
            f"https://www.legacysurvey.org/viewer/jpeg-cutout?ra={self.ra}"
            f"&dec={self.dec}&size=200&layer=dr8&pixscale=0.262&bands=grz"
        )

    @property
    def panstarrs_url(self):
        """Construct URL for public PanSTARRS-1 (PS1) cutout.

        The cutout service doesn't allow directly querying for an image; the
        best we can do is request a page that contains a link to the image we
        want (in this case a combination of the g/r/i filters).

        If this page does not return without PS1_CUTOUT_TIMEOUT seconds then
        we assume that the image is not available and return None.
        """
        ps_query_url = (
            f"https://ps1images.stsci.edu/cgi-bin/ps1cutouts"
            f"?pos={self.ra}+{self.dec}&filter=color&filter=g"
            f"&filter=r&filter=i&filetypes=stack&size=250"
        )
        cutout_url = "/static/images/currently_unavailable.png"
        try:
            response = requests.get(ps_query_url, timeout=PS1_CUTOUT_TIMEOUT)
            response.raise_for_status()
            no_stamps = re.search(
                "No PS1 3PI images were found", response.content.decode()
            )
            if no_stamps:
                cutout_url = "/static/images/outside_survey.png"
            match = re.search(
                'src="//ps1images.stsci.edu.*?"', response.content.decode()
            )
            if match:
                cutout_url = match.group().replace('src="', 'https:').replace('"', '')
        except requests.exceptions.HTTPError as http_err:
            log(f"HTTPError getting thumbnail for {self.id}: {http_err}")
        except requests.exceptions.Timeout as timeout_err:
            log(f"Timeout in getting thumbnail for {self.id}: {timeout_err}")
        except requests.exceptions.RequestException as other_err:
            log(f"Unexpected error in getting thumbnail for {self.id}: {other_err}")
        finally:
            return cutout_url

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

    @property
    def luminosity_distance(self):
        """
        The luminosity distance in Mpc, using either DM or distance data
        in the altdata fields or using the cosmology/redshift. Specifically
        the user can add `dm` (mag), `parallax` (arcsec), `dist_kpc`,
        `dist_Mpc`, `dist_pc` or `dist_cm` to `altdata` and
        those will be picked up (in that order) as the distance
        rather than the redshift.

        Return None if the redshift puts the source not within the Hubble flow
        """

        # there may be a non-redshift based measurement of distance
        # for nearby sources
        if self.altdata:
            if self.altdata.get("dm") is not None:
                # see eq (24) of https://ned.ipac.caltech.edu/level5/Hogg/Hogg7.html
                return (
                    (10 ** (float(self.altdata.get("dm")) / 5.0)) * 1e-5 * u.Mpc
                ).value
            if self.altdata.get("parallax") is not None:
                if float(self.altdata.get("parallax")) > 0:
                    # assume parallax in arcsec
                    return (1e-6 * u.Mpc / float(self.altdata.get("parallax"))).value

            if self.altdata.get("dist_kpc") is not None:
                return (float(self.altdata.get("dist_kpc")) * 1e-3 * u.Mpc).value
            if self.altdata.get("dist_Mpc") is not None:
                return (float(self.altdata.get("dist_Mpc")) * u.Mpc).value
            if self.altdata.get("dist_pc") is not None:
                return (float(self.altdata.get("dist_pc")) * 1e-6 * u.Mpc).value
            if self.altdata.get("dist_cm") is not None:
                return (float(self.altdata.get("dist_cm")) * u.Mpc / 3.085e18).value

        if self.redshift:
            if self.redshift * 2.99e5 * u.km / u.s < 350 * u.km / u.s:
                # stubbornly refuse to give a distance if the source
                # is not in the Hubble flow
                # cf. https://www.aanda.org/articles/aa/full/2003/05/aa3077/aa3077.html
                # within ~5 Mpc (cz ~ 350 km/s) a given galaxy velocty
                # can be between between ~0-500 km/s
                return None
            return (cosmo.luminosity_distance(self.redshift)).to(u.Mpc).value
        return None

    @property
    def dm(self):
        """Distance modulus to the object"""
        dl = self.luminosity_distance
        if dl:
            return 5.0 * np.log10((dl * u.Mpc) / (10 * u.pc)).value
        return None

    @property
    def angular_diameter_distance(self):
        dl = self.luminosity_distance
        if dl:
            if self.redshift and self.redshift * 2.99e5 * u.km / u.s > 350 * u.km / u.s:
                # see eq (20) of https://ned.ipac.caltech.edu/level5/Hogg/Hogg7.html
                return dl / (1 + self.redshift) ** 2
            return dl
        return None

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

        output_shape = time.shape
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


Obj.candidates = relationship(
    Candidate,
    back_populates='obj',
    cascade='delete',
    passive_deletes=True,
    doc="Instances in which this Obj passed a group's filter.",
)

# See source.py for Obj.sources relationship
# It had to be defined there to prevent a circular import.


@event.listens_for(Obj, 'before_delete')
def delete_obj_thumbnails_from_disk(mapper, connection, target):
    for thumb in target.thumbnails:
        if thumb.file_uri is not None:
            try:
                os.remove(thumb.file_uri)
            except (FileNotFoundError, OSError) as e:
                log(f"Error deleting thumbnail file {thumb.file_uri}: {e}")
