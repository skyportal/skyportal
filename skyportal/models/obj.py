__all__ = ['Obj']

import io
import requests
import re
import os
import uuid

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from astropy import coordinates as ap_coord
from astropy.io.votable import parse
from astropy.table import unique
from astropy import units as u
import astroplan
from astroquery.mast import Observations
import conesearch_alchemy
import healpix_alchemy
import numpy as np
import dustmaps.sfd
from dustmaps.config import config

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
from .photometric_series import PhotometricSeries
from .spectrum import Spectrum
from .candidate import Candidate
from .thumbnail import Thumbnail
from .cosmo import cosmo

_, cfg = load_env()
log = make_log('models.obj')

# The minimum signal-to-noise ratio to consider a photometry point as a detection
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]

CUTOUT_TIMEOUT = 10

# download dustmap if required
config['data_dir'] = cfg['misc.dustmap_folder']
required_files = ['sfd/SFD_dust_4096_ngp.fits', 'sfd/SFD_dust_4096_sgp.fits']
if any(
    [
        not os.path.isfile(os.path.join(config['data_dir'], required_file))
        for required_file in required_files
    ]
):
    try:
        dustmaps.sfd.fetch()
    except requests.exceptions.HTTPError:
        pass


def delete_obj_if_all_data_owned(cls, user_or_token):
    from .source import Source

    allow_nonadmins = cfg["misc.allow_nonadmins_delete_objs"]

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

    deletable_photometric_series = PhotometricSeries.query_records_accessible_by(
        user_or_token, mode="delete"
    ).subquery()
    nondeletable_photometric_series = (
        DBSession()
        .query(PhotometricSeries.obj_id)
        .join(
            deletable_photometric_series,
            deletable_photometric_series.c.id == PhotometricSeries.id,
            isouter=True,
        )
        .filter(deletable_photometric_series.c.id.is_(None))
        .distinct(PhotometricSeries.obj_id)
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
            nondeletable_photometric_series,
            nondeletable_photometric_series.c.obj_id == cls.id,
            isouter=True,
        )
        .filter(nondeletable_photometric_series.c.obj_id.is_(None))
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
    # TODO should this column type be decimal? fixed-precision numeric

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
    host = relationship(
        'Galaxy',
        back_populates='objects',
        doc="The Galaxy associated with this source.",
        foreign_keys="Obj.host_id",
    )
    host_id = sa.Column(
        sa.ForeignKey('galaxys.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        doc="The ID of the Galaxy to which this Obj is associated.",
    )
    summary = sa.Column(sa.String, nullable=True, doc="Summary of the obj.")
    summary_history = sa.Column(
        JSONB,
        nullable=True,
        doc="Record of the summaries generated and written about this obj",
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
    mpc_name = sa.Column(
        sa.String,
        doc="Minor planet center name.",
    )
    gcn_crossmatch = sa.Column(
        sa.ARRAY(sa.String),
        doc="List of GCN event dateobs for crossmatched events.",
    )
    tns_name = sa.Column(
        sa.String,
        doc="Transient Name Server name.",
    )
    tns_info = sa.Column(
        JSONB,
        nullable=True,
        doc="TNS info in JSON format",
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

    comments = relationship(
        'Comment',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="Comment.created_at",
        doc="Comments posted about the object.",
    )

    reminders = relationship(
        'Reminder',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="Reminder.created_at",
        doc="Reminders about the object.",
    )

    comments_on_spectra = relationship(
        'CommentOnSpectrum',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="CommentOnSpectrum.created_at",
        doc="Comments posted about spectra belonging to the object.",
    )

    reminders_on_spectra = relationship(
        'ReminderOnSpectrum',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="ReminderOnSpectrum.created_at",
        doc="Reminders about spectra belonging to the object.",
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

    annotations_on_photometry = relationship(
        'AnnotationOnPhotometry',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="AnnotationOnPhotometry.created_at",
        doc="Auto-annotations posted about photometry belonging to the object.",
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

    photstats = relationship(
        'PhotStat',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        single_parent=True,
        passive_deletes=True,
        doc="Photometry statistics associated with the object.",
    )

    detect_photometry_count = sa.Column(
        sa.Integer,
        nullable=True,
        doc="How many times the object was detected above :math:`S/N = phot_detection_threshold (3.0 by default)`.",
    )

    photometric_series = relationship(
        'PhotometricSeries',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        single_parent=True,
        passive_deletes=True,
        order_by="PhotometricSeries.mjd_first",
        doc="Photometric series associated with the object.",
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

    obj_analyses = relationship(
        'ObjAnalysis',
        back_populates='obj',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="Analyses assocated with this obj.",
    )

    sources_in_gcns = relationship(
        "SourcesConfirmedInGCN",
        back_populates="obj",
        passive_deletes=True,
        doc="Sources in a localization.",
    )

    def add_linked_thumbnails(self, thumbnails, session=DBSession):
        """Determine the URLs of the SDSS, Legacy Survey DR9, and
        thumbnails of the object,
        insert them into the Thumbnails table, and link them to the object."""

        if "sdss" in thumbnails:
            session.add(Thumbnail(obj=self, public_url=self.sdss_url, type='sdss'))
        if "ls" in thumbnails:
            session.add(
                Thumbnail(obj=self, public_url=self.legacysurvey_dr9_url, type='ls')
            )
        if "ps1" in thumbnails:
            session.add(Thumbnail(obj=self, public_url=self.panstarrs_url, type="ps1"))
        if "hst" in thumbnails and self.hst_url is not None:
            session.add(Thumbnail(obj=self, public_url=self.hst_url, type="hst"))
        if "chandra" in thumbnails and self.chandra_url is not None:
            session.add(
                Thumbnail(obj=self, public_url=self.chandra_url, type="chandra")
            )

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
    def legacysurvey_dr9_url(self):
        """Construct URL for public Legacy Survey DR9 cutout."""
        return (
            f"https://www.legacysurvey.org/viewer/jpeg-cutout?ra={self.ra}"
            f"&dec={self.dec}&size=200&layer=ls-dr9&pixscale=0.262&bands=grz"
        )

    @property
    def panstarrs_url(self):
        """Construct URL for public PanSTARRS-1 (PS1) cutout.

        The cutout service doesn't allow directly querying for an image; the
        best we can do is request a page that contains a link to the image we
        want (in this case a combination of the g/r/i filters).

        If this page does not return without CUTOUT_TIMEOUT seconds then
        we assume that the image is not available and return None.
        """
        ps_query_url = (
            f"https://ps1images.stsci.edu/cgi-bin/ps1cutouts"
            f"?pos={self.ra}+{self.dec}&filter=color&filter=g"
            f"&filter=r&filter=i&filetypes=stack&size=250"
        )
        cutout_url = "/static/images/currently_unavailable.png"
        try:
            response = requests.get(ps_query_url, timeout=CUTOUT_TIMEOUT)
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
    def hst_url(self):
        """Construct URL for public Hubble Space Telescope (HST) cutouts."""

        mask = {
            'instrument_name': [
                'WFPC2/WFC',
                'PC/WFC',
                'ACS/WFC',
                'ACS/HRC',
                'ACS/SBC',
                'WFC3/UVIS',
                'WFC3/IR',
            ],
            't_exptime': 40,
            'obs_collection': ['HST', 'HLA'],
            'filters': [
                'F220W',
                'F250W',
                'F330W',
                'F344N',
                'F435W',
                'F475W',
                'F550M',
                'F555W',
                'F606W',
                'F625W',
                'F658N',
                'F660N',
                'F660N',
                'F775W',
                'F814W',
                'F850LP',
                'F892N',
                'F098M',
                'F105W',
                'F110W',
                'F125W',
                'F126N',
                'F127M',
                'F128N',
                'F130N',
                'F132N',
                'F139M',
                'F140W',
                'F153M',
                'F160W',
                'F164N',
                'F167N',
                'F200LP',
                'F218W',
                'F225W',
                'F275W',
                'F280N',
                'F300X',
                'F336W',
                'F343N',
                'F350LP',
                'F373N',
                'F390M',
                'F390W',
                'F395N',
                'F410M',
                'F438W',
                'F467M',
                'F469N',
                'F475X',
                'F487N',
                'F502N',
                'F547M',
                'F600LP',
                'F621M',
                'F625W',
                'F631N',
                'F645N',
                'F656N',
                'F657N',
                'F658N',
                'F665N',
                'F673N',
                'F680N',
                'F689M',
                'F763M',
                'F845M',
                'F953N',
                'F122M',
                'F160BW',
                'F185W',
                'F218W',
                'F255W',
                'F300W',
                'F375N',
                'F380W',
                'F390N',
                'F437N',
                'F439W',
                'F450W',
                'F569W',
                'F588N',
                'F622W',
                'F631N',
                'F673N',
                'F675W',
                'F702W',
                'F785LP',
                'F791W',
                'F953N',
                'F1042M',
                'F502N',
            ],
        }

        radius = 1 * u.arcsec
        coord = ap_coord.SkyCoord(self.ra, self.dec, unit='deg')

        table = Observations.query_region(coord, radius=radius)

        # HST-specific masks
        filmask = [table['filters'] == good for good in mask['filters']]
        filmask = [any(idx) for idx in list(map(list, zip(*filmask)))]
        expmask = table['t_exptime'] > mask['t_exptime']
        obsmask = [table['obs_collection'] == good for good in mask['obs_collection']]
        obsmask = [any(idx) for idx in list(map(list, zip(*obsmask)))]
        detmask = [table['instrument_name'] == good for good in mask['instrument_name']]
        detmask = [any(idx) for idx in list(map(list, zip(*detmask)))]

        # Construct and apply mask
        mask = [all(idx) for idx in zip(filmask, expmask, obsmask, detmask)]
        obstable = table[mask]

        if obstable and len(obstable) > 0:
            obsid = obstable['obs_id'][0]
            hst_query_url = (
                f"https://hla.stsci.edu/cgi-bin/fitscut.cgi"
                f"?red={obsid}&amp;RA={self.ra}&amp;DEC={self.dec}&amp;size=256"
                f"&amp;format=jpg&amp;config=ops&amp;asinh=1&amp;autoscale=90"
            )
            return hst_query_url
        else:
            return None

    @property
    def chandra_url(self):
        """Construct URL for public Chandra cutouts.

        The cutout service doesn't allow directly querying for an image; the
        best we can do is request a page that contains a link to the image we
        want.

        If this page does not return without CUTOUT_TIMEOUT seconds then
        we assume that the image is not available and return None.
        """

        radius = 0.1
        query_url = (
            f"https://cxcfps.cfa.harvard.edu/cgi-bin/cda/footprint/get_vo_table.pl?"
            f"pos={self.ra},{self.dec}&size={radius}"
            f"&inst=ACIS-I,ACIS-S&grating=NONE"
        )

        cutout_url = None
        try:
            response = requests.get(query_url, timeout=CUTOUT_TIMEOUT)
            response.raise_for_status()

            f = io.BytesIO(response.text.encode())
            votable = parse(f)
            obsdata = votable.get_first_table().to_table()

            if len(obsdata) > 0:
                table = unique(obsdata, keys='ObsId')
                uri = table['preview_uri'][0].replace('redirect', 'link')
                response = requests.get(uri, timeout=CUTOUT_TIMEOUT)
                match = re.search(
                    'href="https://cdaftp.cfa.harvard.edu.*?"',
                    response.content.decode(),
                )
                if match:
                    cutout_url = match.group().replace('href="', '').replace('"', '')
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
        if isinstance(self.altdata, dict):
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

    @property
    def host_offset(self):
        host = self.host
        if host:
            obj_coord = ap_coord.SkyCoord(self.ra, self.dec, unit='deg')
            host_coord = ap_coord.SkyCoord(host.ra, host.dec, unit='deg')
            sep = obj_coord.separation(host_coord)

            print(sep)
            return sep
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

    @property
    def ebv(self):
        """E(B-V) extinction for the object"""

        coord = ap_coord.SkyCoord(self.ra, self.dec, unit='deg')
        try:
            return float(dustmaps.sfd.SFDQuery()(coord))
        except Exception:
            return None


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
