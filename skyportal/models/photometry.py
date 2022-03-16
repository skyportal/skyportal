__all__ = ['Photometry', 'PHOT_ZP', 'PHOT_SYS']
import os
import uuid
import hashlib
import re

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

import conesearch_alchemy
import numpy as np
import xarray as xr
import arrow

from baselayer.app.models import Base, accessible_by_owner
from baselayer.app.env import load_env

from ..enum_types import allowed_bandpasses, time_stamp_alignment_types
from .group import accessible_by_groups_members, accessible_by_streams_members
from ..utils.cache import array_to_bytes

_, cfg = load_env()

# In the AB system, a brightness of 23.9 mag corresponds to 1 microJy.
# All DB fluxes are stored in microJy (AB).
PHOT_ZP = 23.9
PHOT_SYS = 'ab'

# The minimum signal-to-noise ratio to consider a photometry point as a detection
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]

RE_SLASHES = re.compile(r'^[\w_\-\+\/\\]*$')
RE_NO_SLASHES = re.compile(r'^[\w_\-\+]*$')

MAX_FILEPATH_LENGTH = 255


class Photometry(conesearch_alchemy.Point, Base):
    """Calibrated measurement of the flux of an object through a broadband filter."""

    __tablename__ = 'photometry'

    read = (
        accessible_by_groups_members
        | accessible_by_streams_members
        | accessible_by_owner
    )
    update = delete = accessible_by_owner

    mjd = sa.Column(sa.Float, nullable=False, doc='MJD of the observation.', index=True)
    flux = sa.Column(
        sa.Float,
        doc='Flux of the observation in µJy. '
        'Corresponds to an AB Zeropoint of 23.9 in all '
        'filters.',
        server_default='NaN',
        nullable=False,
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

    origin = sa.Column(
        sa.String,
        nullable=False,
        unique=False,
        index=True,
        doc="Origin from which this Photometry was extracted (if any).",
        server_default='',
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
    streams = relationship(
        "Stream",
        secondary="stream_photometry",
        back_populates="photometry",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Streams associated with this Photometry.",
    )
    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Instrument that took this Photometry.",
    )
    instrument = relationship(
        'Instrument',
        back_populates='photometry',
        doc="Instrument that took this Photometry.",
    )

    followup_request_id = sa.Column(
        sa.ForeignKey('followuprequests.id'), nullable=True, index=True
    )
    followup_request = relationship('FollowupRequest', back_populates='photometry')

    assignment_id = sa.Column(
        sa.ForeignKey('classicalassignments.id'), nullable=True, index=True
    )
    assignment = relationship('ClassicalAssignment', back_populates='photometry')

    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User who uploaded the photometry.",
    )
    owner = relationship(
        'User',
        back_populates='photometry',
        foreign_keys=[owner_id],
        passive_deletes=True,
        cascade='save-update, merge, refresh-expire, expunge',
        doc="The User who uploaded the photometry.",
    )

    @hybrid_property
    def mag(self):
        """The magnitude of the photometry point in the AB system."""
        if not np.isnan(self.flux) and self.flux > 0:
            return -2.5 * np.log10(self.flux) + PHOT_ZP
        else:
            return None

    @hybrid_property
    def e_mag(self):
        """The error on the magnitude of the photometry point."""
        if not np.isnan(self.flux) and self.flux > 0 and self.fluxerr > 0:
            return (2.5 / np.log(10)) * (self.fluxerr / self.flux)
        else:
            return None

    @mag.expression
    def mag(cls):
        """The magnitude of the photometry point in the AB system."""
        return sa.case(
            [
                (
                    sa.and_(cls.flux != 'NaN', cls.flux > 0),  # noqa
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
                        cls.flux != 'NaN', cls.flux > 0, cls.fluxerr > 0
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
        return (
            self.flux / self.fluxerr
            if not np.isnan(self.flux)
            and not np.isnan(self.fluxerr)
            and self.fluxerr != 0
            else None
        )

    @snr.expression
    def snr(self):
        """Signal-to-noise ratio of this Photometry point."""
        return sa.case(
            [
                (
                    sa.and_(
                        self.flux != 'NaN', self.fluxerr != 'NaN', self.fluxerr != 0
                    ),  # noqa
                    self.flux / self.fluxerr,
                )
            ],
            else_=None,
        )


# Deduplication index. This is a unique index that prevents any photometry
# point that has the same obj_id, instrument_id, origin, mjd, flux error,
# and flux as a photometry point that already exists within the table from
# being inserted into the table. The index also allows fast lookups on this
# set of columns, making the search for duplicates a O(log(n)) operation.

Photometry.__table_args__ = (
    sa.Index(
        'deduplication_index',
        Photometry.obj_id,
        Photometry.instrument_id,
        Photometry.origin,
        Photometry.mjd,
        Photometry.fluxerr,
        Photometry.flux,
        unique=True,
    ),
)


class PhotometricSeries(conesearch_alchemy.Point, Base):
    """
    A series of photometric measurements taken
    of the same object with the same telescope and filter,
    continuously from mjd_start to mjd_end.

    To initialize this function user must provide:
    - data: an xarray dataset.
            The data must contain an "mjds" coordinate,
            and either a "fluxes" or a "mags" dataset.
            Other datasets can include "fluxerr" or "magerr",
            and any other auxiliary measurements that are stored
            but generally not used by Skyportal like raw counts,
            backgrounds, fluxes in other apertures, ra/dec, etc.
            All the datasets must have the same length along
            the mjd dimension.
            Auxiliary data (not mags/fluxes) may have additional
            dimensions that are saved but do not affect
            calculations/plotting in Skyportal.
      - series_id: a unique identifier of the set of images from
            which this series was extracted. This is useful
            for finding other objects that were observed
            at the same time as this series.
            Must be a string with only alphanumeric
            characters, underscores, plus/minus signs,
            and slashes (which are respected when
            using the series_id to build the folder tree).
    - series_obj_id: a unique index or name of the object inside
            this observation series. Can be an index of the
            star in the images, or an official designation.
            Does not have to be the same as the obj_id.
            E.g., the same physical object can have
            a different identifier in different series.
            Must be an integer or string with only
            alphanumeric characters, underscores and "+-".
            The total length of the folder tree,
            including the root folder, series_id
            and series_obj_id must be less than
            255 characters.
    """

    __tablename__ = 'photometric_series'

    def __init__(self, data, series_id, series_obj_id):
        self.series_identifier = str(series_id)
        self.series_obj_id = str(series_obj_id)

        if len(data) == 0:
            raise ValueError('Must supply a non-empty data structure.')

        # verify data has all required fields
        if 'fluxes' not in data and 'mags' not in data or 'mjds' not in data:
            raise KeyError(
                'Data input to photometric series must contain at least ["fluxes"|"mags"] and "mjds". '
            )

        self.calc_hash()

        # should we save at the intialization point or only when the row is added to the DB?
        # self.save_data()

        # these can be lazy loaded from file
        self._data = data
        self._mjds = None
        self._fluxes = None
        self._fluxerr = None
        self._mags = None
        self._magerr = None

        # calculate mags from fluxes or vice-versa
        self.calc_flux_mag()

        # figure out some of the summary statistics saved in the DB
        self.calculate_stats()

    @staticmethod
    def flux2mag(fluxes):
        """
        Convert an array of fluxes to an array of magnitudes.
        Assumes a PHOT_ZP which is the same for all filters
        in the AB magnitude system.
        Non-positive flux values are replaced with NaNs.

        Parameters
        ----------
        fluxes: float array
            Array or list of fluxes in units of micro Jansky

        Returns
        -------
        float array
            Magnitude array in the AB system with NaNs
            in every position where the flux is not positive.
        """
        good_points = np.logical_and(np.invert(np.isnan(fluxes)), fluxes > 0)
        mags = -2.5 * np.log10(fluxes, where=good_points) + PHOT_ZP
        mags[np.invert(good_points)] = np.nan
        # should we turn this into a list and convert the NaNs into Nones?
        return mags

    @staticmethod
    def fluxerr2magerr(fluxes, fluxerr):
        """
        Convert flux errors into magnitude errors.

        Parameters
        ----------
        fluxes: float array
            Array or list of fluxes in units of micro Jansky
        fluxerr: float array
            Array or list of errors on each flux measurement,
            in the same units as the fluxes.
        Returns
        -------
        float array
            Magnitude errors array in the AB system with NaNs
            in every position where the flux is not positive.
        """

        good_points = np.logical_and(np.invert(np.isnan(fluxes)), fluxes > 0, fluxerr)
        magerr = (2.5 / np.log(10)) * (fluxerr / fluxes)
        magerr[np.invert(good_points)] = np.nan
        # should we turn this into a list and convert the NaNs into Nones?
        return magerr

    @staticmethod
    def mag2flux(mags):
        """
        Convert AB magnitudes to fluxes in micro Janskies

        Parameters
        ----------
        mags: float array
            Magnitudes array or list in the AB system.

        Returns
        -------
        float array
            Array of fluxes in units of micro Jansky.
        """
        return 10 ** (-0.4 * (mags - PHOT_ZP))

    @staticmethod
    def magerr2fluxerr(mags, magerr):
        """
        Convert magnitude errors to flux errors in micro Janskies

        Parameters
        ----------
        mags: float array
            Magnitudes array in the AB system.
        magerr: float array
            Array or list of errors on the magnitudes.

        Returns
        -------
        float array
            Array of fluxes in units of micro Jansky.
        """

        fluxes = PhotometricSeries.mag2flux(mags)
        return fluxes * magerr * np.log(10) / 2.5

    def calc_flux_mag(self):
        """
        Use the available fluxes to calculate the magnitudes,
        or the available magnitudes to calculate the fluxes.
        Also fills in the mjds field, and the errors if
        they are included in the dataset.
        """

        if 'fluxes' in self._data:
            self._fluxes = self._data['fluxes']
            self._mags = self.flux2mag(self._fluxes)
        elif 'mags' in self._data:
            self._mags = self._data['mags']
            self._fluxes = self.mag2flux(self._mags)
        else:
            raise KeyError('Cannot find "fluxes" or "mags" in photometric data')

        if 'fluxerr' in self._data:
            self._fluxerr = self._data['fluxerr']
            self._magerr = self.fluxerr2magerr(self.fluxes, self._fluxerr)
        elif 'magerr' in self._data:
            self._magerr = self._data['magerr']
            self._fluxerr = self.magerr2fluxerr(self._mags, self._magerr)

    def calculate_stats(self):
        """
        Calculate some summary statistics to be saved in the DB.

        Will fill the JSONB columns of medians, minima and maxima
        and standard deviations for each column in the input data,
        including fluxes, but also any other auxiliary data
        e.g., backgrounds, raw counts, sensor X/Y position.

        Will also find the start/end/midpoint of the
        series MJD, the mean magnitude, the magnitude RMS,
        and the robust RMS using sigma-clipping.
        """

        # get the min/max/media for each column of data
        self.medians = {}
        self.minima = {}
        self.maxima = {}
        self.stds = {}
        for key in self._data:
            self.medians[key] = float(self._data.median('mjds'))
            self.minima[key] = float(self._data.min('mjds'))
            self.maxima[key] = float(self._data.max('mjds'))
            self.stds[key] = float(self._data.std('mjds'))

        self.mjd_first = self.mjds[0]
        self.mjd_last = self.mjds[-1]
        self.mjd_mid = (self.mjd_start + self.mjd_end) / 2
        detection_indices = np.where(self.snr > PHOT_DETECTION_THRESHOLD)[0]
        self.mjd_last_detected = self.mjd[detection_indices[-1]]
        self.num_exp = len(self.mjds)

        # calculate the mean mag, rms and robust median/rms
        self.mean_mag = np.nanmean(self.mags)
        self.rms_mag = np.nanstd(self.mags)
        (self.robust_mag, self.robust_rms) = self.sigma_clipping(self.mags)

        # if RA, Dec or exposure time are given in the auxiliary data:
        for key in ['RA', 'ra']:
            if key in self._data:
                self.ra = self._data[key].median()
                break
        for key in ['Dec', 'DEC', 'dec']:
            if key in self._data:
                self.dec = self._data[key].median()
                break
        for key in [
            'exptime',
            'exp_time',
            'exposure',
            'exposure_time',
            'EXPTIME',
            'EXP_TIME',
        ]:
            if key in self._data:
                self.exp_time = self._data[key].median()
                break

    @staticmethod
    def sigma_clipping(input_values, iterations=3, sigma=3.0):
        """
        Calculate a robust estimate of the mean and scatter
        of the values given to it, using a few iterations
        of finding the median and standard deviation from it,
        and removing any outliers more than "sigma" times
        from that median.
        If the number of samples is less than 5,
        the function returns the nanmedian and nanstd of
        those values without removing outliers.

        Parameters
        ----------
        input_values: one dimensional array of floats
            The input values, either magnitudes or fluxes.
        iterations: int scalar
            Maximum number of iterations to use to remove
            outliers. If no outliers are found, the loop
            is cut short. Default is 3.
        sigma: float scalar
            How many times the standard deviation should
            a measurement fall from the median value,
            to be considered an outlier.
            Default is 3.0.

        Returns
        -------
        2-tuple of floats
            get the median and scatter (RMS) of the distribution,
            without including outliers.
        """

        if len(input_values) < 5:
            return np.nanmedian(input_values), np.nanstd(input_values)

        values = input_values.copy()

        mean_value = np.nanmedian(values)
        scatter = np.nanstd(values)
        num_values_prev = np.sum(np.isnan(values) == 0)

        for i in range(iterations):
            # remove outliers
            values[abs(values - mean_value) / scatter > sigma] = np.nan

            num_values = np.sum(np.isnan(values) == 0)

            # check if there are no new outliers removed this iteration
            # OR don't proceed with too few data points
            if num_values_prev == num_values or num_values < 5:
                break

            num_values_prev = num_values
            mean_value = np.nanmedian(values)
            scatter = np.nanstd(values)

        return mean_value, scatter

    def calc_hash(self):
        md5_hash = hashlib.md5()
        md5_hash.update(array_to_bytes(np.array(self._data)))
        self.hash = md5_hash.hexdigest()

    def load_data(self):
        """
        Load the underlying photometric data from disk.
        """
        self._data = xr.load_dataset(self.filename)

    def save_data(self):
        """
        Save the underlying photometric data to disk.
        """

        # there's a default value but it is best to provide a full path in the config
        root_folder = cfg.get('photometric_series_folder', 'phot_series')

        # the filename can have alphanumeric, underscores, + or -
        self.check_path_string(self.series_obj_id)

        # we can let series_identifier have slashes, which makes subdirs
        self.check_path_string(self.series_identifier, allow_slashes=True)

        # make sure to replace windows style slashes
        subfolder = self.series_identifier.replace("\\", "/")

        filename = f'photo_series_{self.series_obj_id}.nc'

        path = os.path.join(root_folder, subfolder)
        if not os.path.exists(path):
            os.makedirs(path)

        full_name = os.path.join(path, filename)

        if len(full_name) > MAX_FILEPATH_LENGTH:
            raise ValueError(
                f'Full path to file {full_name} is longer than {MAX_FILEPATH_LENGTH} characters.'
            )

        self._data.to_netcdf(full_name)

        self.filename = full_name

    def delete_data(self):
        """
        Delete the underlying photometric data from disk
        """

        if os.path.exists(self.filename):
            os.remove(self.filename)

    read = (
        accessible_by_groups_members
        | accessible_by_streams_members
        | accessible_by_owner
    )
    update = delete = accessible_by_owner

    filename = sa.Column(
        sa.String,
        nullable=False,
        index=True,
        doc="Full path and filename, or URI to the netCDF file storing photometric data.",
    )

    mjd_first = sa.Column(
        sa.Float,
        nullable=False,
        doc='MJD of the first exposure of the series.',
        index=True,
    )

    mjd_mid = sa.Column(
        sa.Float,
        nullable=False,
        doc='MJD of the middle of the observation series.',
        index=True,
    )

    mjd_last = sa.Column(
        sa.Float,
        nullable=False,
        doc='MJD of the last exposure of the series.',
        index=True,
    )

    mjd_last_detected = sa.Column(
        sa.Float,
        nullable=False,
        doc='MJD of the last exposure that was above threshold.',
        index=True,
    )

    detected = sa.Column(
        sa.Boolean,
        nullable=False,
        doc='True if any of the data points are above threshold.',
        index=True,
    )

    series_identifier = sa.Column(
        sa.String,
        nullable=False,
        doc='Unique identifier of the series of images out of which the photometry is generated.',
        index=True,
    )

    series_obj_id = sa.Column(
        sa.String,
        nullable=False,
        doc='Unique identifier of an object inside the series of images out of which the photometry is generated.',
    )

    channel_id = sa.Column(
        sa.String, nullable=False, default='0', doc='Channel of the photometric series.'
    )

    filter = sa.Column(
        allowed_bandpasses,
        nullable=False,
        doc='Filter with which the observation was taken.',
    )

    exp_time = sa.Column(
        sa.Float, nullable=False, doc='Median exposure time of each frame, in seconds.'
    )

    frame_rate = sa.Column(
        sa.Float,
        nullable=False,
        doc='Median frame rate (frequency) of exposures in Hz.',
    )

    num_exp = sa.Column(
        sa.Integer, nullable=False, doc='Number of exposures in the series. '
    )

    time_stamp_alignment = sa.Column(
        time_stamp_alignment_types,
        nullable=False,
        doc='When in each exposure is the mjd timestamp measured: start, middle, or end.',
        default='middle',
    )

    ra_unc = sa.Column(sa.Float, doc="Uncertainty of ra position [arcsec]")
    dec_unc = sa.Column(sa.Float, doc="Uncertainty of dec position [arcsec]")

    altdata = sa.Column(JSONB, doc="Arbitrary metadata in JSON format..")

    upload_id = sa.Column(
        sa.String,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        doc="ID of the batch in which this Photometry was uploaded (for bulk deletes).",
    )

    origin = sa.Column(
        sa.String,
        nullable=False,
        unique=False,
        index=True,
        doc="Origin from which this photometric series was extracted (if any).",
        server_default='',
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the photometric series' Obj.",
    )
    obj = relationship(
        'Obj', back_populates='photometric_series', doc="The photometric series' Obj."
    )

    groups = relationship(
        "Group",
        secondary="group_photometric_series",
        back_populates="photometric_series",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can access this photometric series.",
    )

    streams = relationship(
        "Stream",
        secondary="stream_photometric_series",
        back_populates="photometric_series",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Streams associated with this photometric series.",
    )

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Instrument that took this photometric series.",
    )
    instrument = relationship(
        'Instrument',
        back_populates='photometric_series',
        doc="Instrument that took this photometric series.",
    )

    followup_request_id = sa.Column(
        sa.ForeignKey('followuprequests.id'), nullable=True, index=True
    )
    followup_request = relationship(
        'FollowupRequest', back_populates='photometric_series'
    )

    assignment_id = sa.Column(
        sa.ForeignKey('classicalassignments.id'), nullable=True, index=True
    )
    assignment = relationship(
        'ClassicalAssignment', back_populates='photometric_series'
    )

    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User who uploaded the photometric series.",
    )
    owner = relationship(
        'User',
        back_populates='photometric_series',
        foreign_keys=[owner_id],
        passive_deletes=True,
        cascade='save-update, merge, refresh-expire, expunge',
        doc="The User who uploaded the photometric series.",
    )

    mean_mag = sa.Column(sa.Float, doc='The average magnitude using nanmean.')
    rms_mag = sa.Column(sa.Float, doc='Root Mean Square of the magnitudes. ')
    robust_mag = sa.Column(
        sa.Float,
        doc='Robust estimate of the median magnitude, using outlier rejection.',
    )
    robust_rms = sa.Column(
        sa.Float, doc='Robust estimate of the magnitude RMS, using outlier rejection.'
    )

    medians = sa.Column(
        JSONB,
        doc='Summary statistics on this series. The nanmedian value of each column in data.',
    )

    maxima = sa.Column(
        JSONB,
        doc='Summary statistics on this series. The nanmax value of each column in data.',
    )

    minima = sa.Column(
        JSONB,
        doc='Summary statistics on this series. The nanmin value of each column in data.',
    )

    stds = sa.Column(
        JSONB,
        doc='Summary statistics on this series. The nanstd value of each column in data.',
    )

    hash = sa.Column(
        sa.String,
        nullable=False,
        unique=True,
        doc='MD5sum hash of the data to be saved to file. Prevents duplications.',
    )

    @staticmethod
    def check_path_string(string, allow_slashes=False):
        if allow_slashes:
            reg = RE_SLASHES
        else:
            reg = RE_NO_SLASHES

        if not reg.match(string):
            raise ValueError(f'Illegal characters in string "{string}". ')

    @hybrid_property
    def data(self):
        """Lazy load the data dictionary"""
        if self._data is None:
            self.load_data()
        return self._data

    @hybrid_property
    def mjds(self):
        """
        Modified Julian dates for each exposure.
        """
        if self._mjds is None:  # lazy load
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._mjds)

    @hybrid_property
    def fluxes(self):
        """
        Fluxes of each observation in µJy.
        Corresponds to an AB Zeropoint of 23.9 in all filters.
        """
        if self._fluxes is None:
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._fluxes)

    @hybrid_property
    def fluxerr(self):
        """
        Gaussian error on the flux in µJy.
        """
        if self._fluxerr is None:  # lazy load
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._fluxerr)

    @hybrid_property
    def mags(self):
        """The magnitude of each point in the AB system."""
        if self._mags is None:  # lazy load
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._mags)

    @hybrid_property
    def magerr(self):
        """The error on the magnitude of each photometry point."""
        if self._magerr is None:  # lazy load
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._magerr)

    @hybrid_property
    def jd_first(self):
        """Julian Date of the first exposure of the series."""
        return self.mjd_first + 2_400_000.5

    @hybrid_property
    def jd_mid(self):
        """Julian Date of the middle of the series."""
        return self.mjd_mid + 2_400_000.5

    @hybrid_property
    def jd_last(self):
        """Julian Date of the last exposure of the series."""
        return self.mjd_last + 2_400_000.5

    @hybrid_property
    def iso_first(self):
        """UTC ISO timestamp (ArrowType) of the start of the series. """
        return arrow.get((self.mjd_first - 40_587) * 86400.0)

    @iso_first.expression
    def iso_first(cls):
        """UTC ISO timestamp (ArrowType) of the first exposure of the series. """
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_first - 40_587) * 86400.0)

    @hybrid_property
    def iso_mid(self):
        """UTC ISO timestamp (ArrowType) of the middle of the series. """
        return arrow.get((self.mjd_mid - 40_587) * 86400.0)

    @iso_mid.expression
    def iso_mid(cls):
        """UTC ISO timestamp (ArrowType) of the middle of the series. """
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_mid - 40_587) * 86400.0)

    @hybrid_property
    def iso_last(self):
        """UTC ISO timestamp (ArrowType) of the last exposure of the series. """
        return arrow.get((self.mjd_last - 40_587) * 86400.0)

    @iso_last.expression
    def iso_last(cls):
        """UTC ISO timestamp (ArrowType) of the last exposure of the series. """
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_last - 40_587) * 86400.0)

    @hybrid_property
    def iso_last_detected(self):
        """UTC ISO timestamp (ArrowType) of the last exposure of the series. """
        return arrow.get((self.mjd_last_detected - 40_587) * 86400.0)

    @iso_last_detected.expression
    def iso_last_detected(cls):
        """UTC ISO timestamp (ArrowType) of the last exposure of the series. """
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_last_detected - 40_587) * 86400.0)

    @hybrid_property
    def snr(self):
        """Signal-to-noise ratio of each measurement"""
        if self.fluxerr is not None and len(self.fluxerr) == len(self.flux):
            err = np.maximum(
                self.fluxerr, self.robust_rms
            )  # assume the worst of the two errors
            return self.flux / err

        return self.flux / self.robust_rms
