__all__ = [
    'PhotometricSeries',
    'REQUIRED_ATTRIBUTES',
    'INFERABLE_ATTRIBUTES',
    'OPTIONAL_ATTRIBUTES',
    'DATA_TYPES',
    'verify_data',
    'infer_metadata',
    'verify_metadata',
]
import os
import re
import hashlib
import arrow

import numpy as np

import pandas as pd

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import relationship, reconstructor
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

import conesearch_alchemy

from baselayer.app.models import Base, accessible_by_owner
from baselayer.app.env import load_env

from ..enum_types import allowed_bandpasses, time_stamp_alignment_types
from .group import accessible_by_groups_members, accessible_by_streams_members

from .photometry import PHOT_ZP
from ..utils.hdf5_files import dump_dataframe_to_bytestream


_, cfg = load_env()

PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]

RE_SLASHES = re.compile(r'^[\w_\-\+\/\\]*$')
RE_NO_SLASHES = re.compile(r'^[\w_\-\+]*$')
MAX_FILEPATH_LENGTH = 255

# these must be given explicitly to the initialization function
REQUIRED_ATTRIBUTES = [
    'series_name',
    'series_obj_id',
    'obj_id',
    'instrument_id',
    'owner_id',
    'group_ids',
    'stream_ids',
]
# these can either be given directly to the constructor or inferred from the data columns
INFERABLE_ATTRIBUTES = ['ra', 'dec', 'exp_time', 'filter']
# these are optional and can be given to the constructor
OPTIONAL_ATTRIBUTES = [
    'channel',
    'origin',
    'limiting_mag',
    'magref',
    'e_magref',
    'ref_flux',
    'ref_fluxerr',
    'ra_unc',
    'dec_unc',
    'followup_request_id',
    'assignment_id',
    'time_stamp_alignment',
    'altdata',
]

DATA_TYPES = {
    'series_name': str,
    'series_obj_id': str,
    'obj_id': str,
    'instrument_id': int,
    'owner_id': int,
    'group_ids': [int],
    'stream_ids': [int],
    'channel': str,
    'time_stamp_alignment': str,
    'magref': float,
    'e_magref': float,
    'ref_flux': float,
    'ref_fluxerr': float,
    'ra': float,
    'dec': float,
    'ra_unc': float,
    'dec_unc': float,
    'exp_time': float,
    'filter': str,
    'altdata': dict,
    'origin': str,
    'followup_request_id': int,
    'assignment_id': int,
}


def verify_data(data):
    """
    Verifies that the given data
    is a pandas DataFrame.
    Raises a TypeError if not.
    Checks that the data contains the required
    columns (flux or mag, and mjd).
    Will raise a KeyError if not.

    Parameters
    ----------
    data: pandas.DataFrame
        The data to verify.

    """
    if not isinstance(data, pd.DataFrame) or len(data.index) == 0:
        raise ValueError('Must supply a non-empty DataFrame. ')

    if not any([c in data for c in ['flux', 'fluxes', 'mag', 'mags', 'magnitudes']]):
        raise KeyError(
            'Input to photometric series must contain '
            '"flux", "fluxes", "mag", "mags" or "magnitudes". '
        )
    if not any([c in data for c in ['mjd', 'mjds']]):
        raise KeyError(
            'Input to photometric series must contain ' 'a "mjd" or "mjds" column. '
        )


def infer_metadata(data):
    """
    Attempts to recover some object
    parameters (metadata) like ra/dec,
    from the given dataframe.

    Parameters
    ----------
    data: pandas.DataFrame
        The data to extract metadata from.

    Returns
    -------
    metadata: dict
        The metadata recovered from the data.
        Could include ra, dec, filter, exp_time.
    """
    metadata = {}

    for key in ['RA', 'ra', 'Ra']:
        if key in data:
            metadata['ra'] = data[key].median()
            break
    for key in ['Dec', 'DEC', 'dec']:
        if key in data:
            metadata['dec'] = data[key].median()
            break
    for key in [
        'exptime',
        'exp_time',
        'exposure',
        'exposure_time',
        'EXPTIME',
        'EXP_TIME',
    ]:
        if key in data:
            metadata['exp_time'] = data[key].median()
            break
    for key in ['filter', 'FILTER', 'Filter', 'filtercode']:
        if key in data and len(data[key].unique()) == 1:
            metadata['filter'] = data[key][0]
            break
    for key in ['lim_mag', 'limmag', 'limiting_mag', 'limiting_magnitude']:
        if key in data:
            metadata['limiting_mag'] = data[key].median()
            break

    return metadata


def verify_metadata(metadata):
    """
    Verifies that the required arguments
    are all given in the metadata dictionary,
    and that there are no unidentified keys.
    Raises a KeyError if not.
    Assumes that metadata that could have been
    inferred from the data has already been added to metadata.
    Verifies that all values are in the correct format.
    Will convert values that can be cast into the
    correct format if possible. Raises a ValueError
    if it cannot cast any of the values.

    Parameters
    ----------
    metadata: dict
        The metadata to verify.
        Assumes that metadata that could have been
        inferred from the data has already been added to metadata.

    Returns
    -------
    verified_metadata: dict
        The verified metadata.
        Any values that could be cast into the correct format
        have been cast.
    """
    missing_keys = []
    for key in REQUIRED_ATTRIBUTES + INFERABLE_ATTRIBUTES:
        if key not in metadata:
            missing_keys.append(key)
    if len(missing_keys) > 0:
        raise ValueError(f'The following keys are missing: {missing_keys}')

    unknown_keys = []
    for key in metadata.keys():
        if key not in REQUIRED_ATTRIBUTES + INFERABLE_ATTRIBUTES + OPTIONAL_ATTRIBUTES:
            unknown_keys.append(key)
    if len(unknown_keys) > 0:
        raise ValueError(f'Unknown keys in metadata: {unknown_keys}')

    verified_metadata = {}
    for key in metadata.keys():
        try:
            # make sure each value can be cast to the correct type
            data_type = DATA_TYPES.get(key)
            if data_type in (str, int, float, dict):
                verified_metadata[key] = data_type(metadata[key])
            elif data_type == list:
                verified_metadata[key] = list(metadata[key])
                if len(data_type) == 1:  # e.g., [int]
                    verified_metadata[key] = [
                        data_type[0](v) for v in verified_metadata[key]
                    ]
            # can add more types here if needed
            else:
                verified_metadata[key] = metadata[key]
        except Exception as e:
            raise ValueError(f'Could not cast {key} to the correct type: {e}')

    return verified_metadata


class PhotometricSeries(conesearch_alchemy.Point, Base):
    """
    A series of photometric measurements taken
    of the same object with the same telescope and filter,
    continuously from mjd_first to mjd_last.

    To initialize this function user must provide:
    - data: a pandas dataframe.
            The data must contain a "mjds" column,
            and either a "flux", "fluxes", "mag", "mags" or a "magnitudes"
            columns. Other columns can include "fluxerr" or "magerr",
            and any other auxiliary measurements that are stored
            but generally not used by SkyPortal like raw counts,
            backgrounds, fluxes in other apertures, ra/dec, etc.
      - series_name: a unique identifier of the set of images from
            which this series was extracted. This is useful
            for finding other objects that were observed
            at the same time as this series.
            Must be a string with only alphanumeric
            characters, underscores, plus/minus signs,
            and slashes (which are respected when
            using the series_name to build the folder tree).
            Examples of series names could be TESS sector number,
            or "date/object_name" or "date/field_number".
    - series_obj_id: a unique index or name of the object inside
            this observation series. Can be an index of the
            star in the images, or an official designation.
            Does not have to be the same as the obj_id.
            E.g., the same physical object can have
            a different identifier in different series.
            Must be an integer or string with only
            alphanumeric characters, underscores and "+-".
            The total length of the folder tree,
            including the root folder, series_name
            and series_obj_id must be less than
            255 characters.
    """

    __tablename__ = 'photometric_series'

    def __init__(self, data, **kwargs):
        """
        Create a photometric series object.
        When initializing, the user must provide:
        data as a pandas DataFrame.
        The data must have at least two columns:
        "mjds" and either "fluxes" or "mags".
        Some other keywords that can be given
        are included in three lists:
        REQUIRED_ATTRIBUTES, INFERABLE_ATTRIBUTES, OPTIONAL_ATTRIBUTES.
        The REQUIRED_ATTRIBUTES must be given explicitly,
        as they identify the object and series.
        The INFERABLE_ATTRIBUTES can be given either
        directly to the constructor or inferred from the data columns
        (e.g., if there's an "ra" column, the median of that column
        is used, if it doesn't exist it MUST be supplied directly).
        The OPTIONAL_ATTRIBUTES can be given or they remain None
        (or the default value for each attribute).

        """

        all_keys = REQUIRED_ATTRIBUTES + INFERABLE_ATTRIBUTES + OPTIONAL_ATTRIBUTES
        for key in kwargs.keys():
            if key not in all_keys:
                raise ValueError(f'Unknown keyword argument "{key}"')

        required_keys = REQUIRED_ATTRIBUTES + INFERABLE_ATTRIBUTES
        for key in required_keys:
            if key not in kwargs.keys():
                raise ValueError(f'"{key}" is a required attribute.')
            setattr(self, key, kwargs[key])

        verify_data(data)

        # additional verification is done in the handler!

        # these can be lazy loaded from data
        self._mjds = None
        self._fluxes = None
        self._fluxerr = None
        self._mags = None
        self._magerr = None
        self._data_bytes = None

        # these should be filled out by sqlalchemy when committing
        self.group_ids = None
        self.stream_ids = None

        # when setting data into the the public "data"
        # attribute, we check the validity of the data
        # and also call calc_flux_mag() and calc_stats()
        self.data = data

        for k in all_keys:
            if k in kwargs:
                setattr(self, k, kwargs[k])

        self.calc_hash()

    @reconstructor
    def init_on_load(self):
        """
        This is called when the object
        is loaded from the database.
        ref: https://docs.sqlalchemy.org/en/14/orm/constructors.html
        """
        self._mjds = None
        self._fluxes = None
        self._fluxerr = None
        self._mags = None
        self._magerr = None
        self._data_bytes = None

        # these should be filled out by sqlalchemy when loading relationships
        self.group_ids = None
        self.stream_ids = None

        try:
            self.load_data()
            self.calc_flux_mag()
            self.calc_stats()
        except Exception:
            pass  # silently fail to load

    def to_dict(self, data_format='json'):
        """
        Convert the object into a dictionary.

        Parameters
        ----------
        data_format : str
            The format of the data to return.
            Can be "json" or "hdf5' or 'none'.
        """
        # use the baselayer base model's method
        d = super().to_dict()

        if data_format.lower() == 'json':
            output_data = self.data.to_dict(orient='list')
        elif data_format.lower() == 'hdf5':
            output_data = dump_dataframe_to_bytestream(
                self.data, self.get_metadata(), encode=True
            )
        elif data_format.lower() == 'none':
            output_data = None
        else:
            raise ValueError(
                f'Invalid dataFormat: "{data_format}". Use "json", "hdf5", or "none".'
            )

        d['data'] = output_data
        return d

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
            Array or list of fluxes in units of micro-Jansky

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

        good_points = np.logical_and(
            np.invert(np.isnan(fluxes)), fluxes > 0, fluxerr > 0
        )
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
        Also, fills-in the mjds field, and the errors if
        they are included in the dataset.
        """

        if 'flux' in self._data:
            self._fluxes = self._data['flux']
            self._mags = self.flux2mag(self._fluxes)
        elif 'fluxes' in self._data:
            self._fluxes = self._data['fluxes']
            self._mags = self.flux2mag(self._fluxes)
        elif 'mag' in self._data:
            self._mags = self._data['mag']
            self._fluxes = self.mag2flux(self._mags)
        elif 'mags' in self._data:
            self._mags = self._data['mags']
            self._fluxes = self.mag2flux(self._mags)
        elif 'magnitudes' in self._data:
            self._mags = self._data['magnitudes']
            self._fluxes = self.mag2flux(self._mags)
        else:
            raise KeyError('Cannot find "fluxes" or "mags" in photometric data')

        if 'fluxerr' in self._data:
            self._fluxerr = self._data['fluxerr']
            self._magerr = self.fluxerr2magerr(self.fluxes, self._fluxerr)
        elif 'magerr' in self._data:
            self._magerr = self._data['magerr']
            self._fluxerr = self.magerr2fluxerr(self._mags, self._magerr)
        else:
            self._magerr = np.array([])
            self._fluxerr = np.array([])

        if 'mjd' in self._data:
            self._mjds = self._data['mjd']
        elif 'mjds' in self._data:
            self._mjds = self._data['mjds']
        else:
            raise KeyError('Cannot find "mjd" or "mjds" in photometric data')

    def calc_stats(self):
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
        # calculate the mean mag, rms and robust median/rms
        self.mean_mag = float(np.nanmean(self.mags))
        self.rms_mag = float(np.nanstd(self.mags))
        (self.robust_mag, self.robust_rms) = self.sigma_clipping(self.mags)

        self.median_snr = float(np.nanmedian(self.snr))
        self.best_snr = float(np.nanmax(self.snr))
        self.worst_snr = float(np.nanmin(self.snr))

        # get the min/max/media for each column of data
        self.medians = {}
        self.minima = {}
        self.maxima = {}
        self.stds = {}
        for key in self._data:
            self.medians[key] = float(np.nanmedian(self.mjds))
            self.minima[key] = float(np.nanmin(self.mjds))
            self.maxima[key] = float(np.nanmax(self.mjds))
            self.stds[key] = float(np.nanstd(self.mjds))

        # This assumes the data is sorted by mjd!
        self.mjd_first = float(self.mjds[0])
        self.mag_first = float(self.mags[0])
        self.mjd_last = float(self.mjds[-1])
        self.mag_last = float(self.mags[-1])
        self.mjd_mid = (self.mjd_first + self.mjd_last) / 2

        detection_indices = np.where(self.snr > PHOT_DETECTION_THRESHOLD)[0]
        if len(detection_indices) > 0:
            self.mjd_last_detected = float(self.mjds[detection_indices[-1]])
            self.mag_last_detected = float(self.mags[detection_indices[-1]])
            self.is_detected = True
        else:
            self.mjd_last_detected = None
            self.mag_last_detected = None
            self.is_detected = False
        self.num_exp = len(self.mjds)

        # time between exposures, in seconds
        dt = float(np.nanmedian(np.diff(self.mjds)) * 24 * 3600)
        self.frame_rate = 1 / dt

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
            mean_value = np.nanmean(values)
            scatter = np.nanstd(values)

        return float(mean_value), float(scatter)

    def get_metadata(self):
        """
        Get all the properties that cannot be
        ascertained directly from the data
        into a single dictionary.

        Any attributes that are None will not
        be added to the dictionary.
        """
        output = {}
        for key in REQUIRED_ATTRIBUTES + INFERABLE_ATTRIBUTES + OPTIONAL_ATTRIBUTES:
            if getattr(self, key) is not None:
                output[key] = getattr(self, key)

        return output

    def get_data_with_extra_columns(self):
        """
        Return a copy of the underlying dataframe,
        but add a few columns that could be needed
        for e.g., plotting.

        The columns are only added if they do not already
        exist in the dataframe, and the values would
        simply be copied from the global value.
        E.g., if there isn't an exp_time column,
        it will be added with the value of the global
        self.exp_time.

        Columns that can be added include:
        id, ra, dec, ra_unc, dec_unc, exp_time,
        filter, limiting_mag, snr, obj_id,
        instrument_id, instrument_name,
        created_at, origin.

        If magref/ref_flux is given for this series,
        will also add the relevant columns:
        magtot, magtot_err, tot_flux, tot_flux_err.
        If any of these columns exsit, they are
        left unchanged.
        """
        df = self.data.copy()
        df['id'] = self.id
        df['origin'] = self.origin
        df['obj_id'] = self.obj_id
        if 'ra' not in df:
            df['ra'] = self.ra
        if 'dec' not in df:
            df['dec'] = self.dec
        if 'ra_unc' not in df:
            df['ra_unc'] = self.ra_unc
        if 'dec_unc' not in df:
            df['dec_unc'] = self.dec_unc
        if 'filter' not in df:
            df['filter'] = self.filter
        if 'snr' not in df:
            df['snr'] = self.snr

        df['instrument_id'] = self.instrument_id
        df['instrument'] = self.instrument.name
        df['telescope'] = self.instrument.telescope.nickname
        df['created_at'] = self.created_at

        if self.ref_flux is not None:
            if 'magtot' not in df:
                df['magtot'] = self.magtot
            if 'e_magtot' not in df:
                df['e_magtot'] = self.e_magtot
            if 'tot_flux' not in df:
                df['tot_flux'] = self.tot_flux
            if 'tot_fluxerr' not in df:
                df['tot_fluxerr'] = self.tot_fluxerr

        return df

    def load_data(self):
        """
        Load the underlying photometric data from disk.
        """
        with pd.HDFStore(self.filename, mode='r') as store:
            keys = list(store.keys())
            if len(keys) != 1:
                raise ValueError('HDF5 file must contain exactly one data table')
            self._data = store[keys[0]]

    def get_data_bytes(self):
        """
        Return a bytes array representation of the
        data that is going to be saved to disk.
        This is lazy loaded if it is saved in self._data_bytes,
        which is calculated from self.data along with
        some metadata from this object.

        Returns
        -------
        bytes
            The data to be saved to disk.
        """
        if self._data_bytes is None:
            # get the data to be saved to disk
            # without actually writing anything yet
            # ref: https://github.com/pandas-dev/pandas/issues/9246#issuecomment-74041497
            with pd.HDFStore(
                'test_file.h5',
                mode='w',
                driver="H5FD_CORE",
                driver_core_backing_store=0,
            ) as store:
                # store['phot_series'] = self._data
                # to avoid HDF5 storing the current timestamp in the file
                # and thus messing up the checksum, we use track_times=False
                # the index=None appears to also be needed:
                # ref: https://github.com/pandas-dev/pandas/pull/32700#issuecomment-666383395
                # ref: https://github.com/pandas-dev/pandas/blob/b1b70c7390e589bbfa0d8896aa76e64bec0cf51e/pandas/tests/io/pytables/test_store.py#L324
                store.put(
                    'phot_series',
                    self._data,
                    format='table',
                    index=None,
                    track_times=False,
                )
                store.get_storer('phot_series').attrs.metadata = self.get_metadata()

                self._data_bytes = store._handle.get_file_image()

        return self._data_bytes

    def calc_hash(self):
        """
        Calculate the hash of the data on disk.
        This uses the data_bytes property,
        and could cause it to be compiled on the
        first call to this function.
        That data is kept for later when
        it can be dumped to file.
        """

        # first make sure to order the lists
        # so that the hash is the same
        self.group_ids = sorted(self.group_ids)
        self.stream_ids = sorted(self.stream_ids)

        self.hash = hashlib.md5()
        self.hash.update(self.get_data_bytes())
        self.hash = self.hash.hexdigest()

    def make_full_name(self):
        """
        Make the full name for the data associated
        with this photometry series on disk.
        This includes the full path.

        Returns
        -------
        full_name: str
            The full name of the file on disk.
        """
        # there's a default value, but it is best to provide a full path in the config
        root_folder = cfg.get('photometric_series_folder', 'persistentdata/phot_series')
        basedir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
        )
        root_folder = os.path.join(basedir, root_folder)

        # the filename can have alphanumeric, underscores, + or -
        self.check_path_string(self.series_obj_id)

        # we can let series_name have slashes, which makes subdirs
        self.check_path_string(self.series_name, allow_slashes=True)

        # make sure to replace windows style slashes
        subfolder = self.series_name.replace("\\", "/")

        origin = '_' + self.origin.replace(" ", "_") if self.origin else ''
        channel = '_' + self.channel.replace(" ", "_") if self.channel else ''

        filename = (
            f'series_{self.series_obj_id}_inst_{self.instrument_id}{channel}{origin}.h5'
        )

        path = os.path.join(root_folder, subfolder)

        full_name = os.path.join(path, filename)

        if len(full_name) > MAX_FILEPATH_LENGTH:
            raise ValueError(
                f'Full path to file {full_name} is longer than {MAX_FILEPATH_LENGTH} characters.'
            )

        return full_name, path

    @staticmethod
    def check_path_string(string, allow_slashes=False):
        """
        Checks that a string is a valid path string.
        Will only allow alphanumeric, plus/minus and underscores.
        If allow_slashes is True, will also allow (back) slashes
        Returns none, but will raise ValueError if string is invalid.
        """
        if allow_slashes:
            reg = RE_SLASHES
        else:
            reg = RE_NO_SLASHES

        if not reg.match(string):
            raise ValueError(f'Illegal characters in string "{string}". ')

    def save_data(self, temp=False):
        """
        Save the underlying photometric data to disk.

        Use temp=True to save a temporary file
        (same file, appended with .tmp).
        """

        # make sure no changes were made since object was initialized
        self.calc_hash()

        full_name, path = self.make_full_name()

        if not os.path.exists(path):
            os.makedirs(path)

        file_to_write = full_name
        if temp:
            file_to_write += '.tmp'

        with open(file_to_write, 'wb') as f:
            f.write(self.get_data_bytes())

        self.filename = full_name

    def move_temp_data(self):
        """Rename a temp data file to not have the .tmp extension."""
        full_name, _ = self.make_full_name()
        if os.path.isfile(full_name + '.tmp'):
            os.rename(full_name + '.tmp', full_name)

    def delete_data(self, temp=False):
        """
        Delete the underlying photometric data from disk.
        If temp=True, delete the temporary file.
        """
        if self.filename and os.path.exists(self.filename):
            file_to_delete = self.filename
            if temp:
                file_to_delete += '.tmp'
            os.remove(file_to_delete)

    read = (
        accessible_by_groups_members
        | accessible_by_streams_members
        | accessible_by_owner
    )
    update = delete = accessible_by_owner

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the photometric series' Obj.",
    )
    obj = relationship(
        'Obj', back_populates='photometric_series', doc="The photometric series' Obj."
    )

    series_name = sa.Column(
        sa.String,
        nullable=False,
        index=True,
        doc='Unique identifier of the series of images '
        'out of which the photometry is generated. '
        'E.g., the TESS sector number. ',
    )

    series_obj_id = sa.Column(
        sa.String,
        nullable=False,
        index=True,
        doc='Unique identifier of an object inside '
        'the series of images out of which the '
        'photometry is generated. '
        'E.g., could be the TESS TICID. ',
    )

    filter = sa.Column(
        allowed_bandpasses,
        nullable=False,
        index=True,
        doc='Filter with which the observation was taken.',
    )

    channel = sa.Column(
        sa.String,
        nullable=False,
        default='',
        index=True,
        doc='Name of channel of the photometric series.',
    )

    origin = sa.Column(
        sa.String,
        nullable=False,
        default='',
        index=True,
        doc="Origin from which this photometric series was extracted (if any).",
    )

    filename = sa.Column(
        sa.String,
        nullable=False,
        index=True,
        unique=True,
        doc="Full path and filename, or URI to the HDF5 file storing photometric data.",
    )

    mjd_first = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc='MJD of the first exposure of the series.',
    )
    mag_first = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc='Magnitude of the first exposure of the series.',
    )

    mjd_mid = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc='MJD of the middle of the observation series.',
    )

    mjd_last = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc='MJD of the last exposure of the series.',
    )
    mag_last = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc='Magnitude of the last exposure of the series.',
    )

    mjd_last_detected = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='MJD of the last exposure that was above threshold.',
    )
    mag_last_detected = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Magnitude of the last exposure that was above threshold.',
    )

    is_detected = sa.Column(
        sa.Boolean,
        nullable=False,
        index=True,
        doc='True if any of the data points are above threshold.',
    )

    exp_time = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc='Median exposure time of each frame, in seconds.',
    )

    frame_rate = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc='Median frame rate (frequency) of exposures in Hz.',
    )

    num_exp = sa.Column(
        sa.Integer,
        nullable=False,
        index=True,
        doc='Number of exposures in the series. ',
    )

    time_stamp_alignment = sa.Column(
        time_stamp_alignment_types,
        nullable=False,
        default='middle',
        doc='When in each exposure is the mjd timestamp measured: start, middle, or end.',
    )

    ra_unc = sa.Column(
        sa.Float, nullable=True, doc="Uncertainty of ra position [arcsec]"
    )
    dec_unc = sa.Column(
        sa.Float, nullable=True, doc="Uncertainty of dec position [arcsec]"
    )

    limiting_mag = sa.Column(
        sa.Float,
        nullable=False,
        default=np.nan,
        index=True,
        doc='Limiting magnitude of the photometric series. '
        'If each point in the series has a limiting magnitude, '
        'this will be the median value of those limiting magnitudes. ',
    )

    ref_flux = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc="Reference flux. E.g., "
        "of the source before transient started, "
        "or the mean flux of a variable source.",
    )

    ref_fluxerr = sa.Column(
        sa.Float, nullable=True, doc="Uncertainty on the reference flux."
    )

    altdata = sa.Column(JSONB, default={}, doc="Arbitrary metadata in JSON format.")

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

    mean_mag = sa.Column(
        sa.Float, index=True, doc='The average magnitude using nanmean.'
    )
    rms_mag = sa.Column(
        sa.Float, index=True, doc='Root Mean Square of the magnitudes. '
    )
    robust_mag = sa.Column(
        sa.Float,
        doc='Robust estimate of the median magnitude, using outlier rejection.',
    )
    robust_rms = sa.Column(
        sa.Float, doc='Robust estimate of the magnitude RMS, using outlier rejection.'
    )

    median_snr = sa.Column(
        sa.Float,
        index=True,
        doc='Median signal to noise ratio of all measurements.',
    )

    best_snr = sa.Column(
        sa.Float,
        index=True,
        doc='Highest signal to noise ratio among all measurements.',
    )

    worst_snr = sa.Column(
        sa.Float,
        index=True,
        doc='Lowest signal to noise ratio among all measurements.',
    )

    medians = sa.Column(
        JSONB,
        index=True,
        doc='Summary statistics on this series. The nanmedian value of each column in data.',
    )

    maxima = sa.Column(
        JSONB,
        index=True,
        doc='Summary statistics on this series. The nanmax value of each column in data.',
    )

    minima = sa.Column(
        JSONB,
        index=True,
        doc='Summary statistics on this series. The nanmin value of each column in data.',
    )

    stds = sa.Column(
        JSONB,
        index=True,
        doc='Summary statistics on this series. The nanstd value of each column in data.',
    )

    hash = sa.Column(
        sa.String,
        nullable=False,
        unique=True,
        index=True,
        doc='MD5sum hash of the data to be saved to file. Prevents duplications.',
    )

    autodelete = sa.Column(
        sa.Boolean,
        nullable=False,
        default=True,
        doc='Whether the data file should be automatically deleted '
        'from disk when this row is deleted from database. ',
    )

    @property
    def data(self):
        """Lazy load the data dictionary"""
        if self._data is None:
            self.load_data()
        return self._data

    @data.setter
    def data(self, data):
        """Set the underlying pandas dataframe"""
        verify_data(data)

        self._data = data

        self.calc_flux_mag()
        self.calc_stats()

    @property
    def mjds(self):
        """
        Modified Julian dates for each exposure.
        """
        if self._mjds is None:  # lazy load
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._mjds)

    @property
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

    @property
    def fluxerr(self):
        """
        Gaussian error on the flux in µJy.
        """
        if self._fluxerr is None:  # lazy load
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._fluxerr)

    @property
    def mags(self):
        """The magnitude of each point in the AB system."""
        if self._mags is None:  # lazy load
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._mags)

    @property
    def magerr(self):
        """The error on the magnitude of each photometry point."""
        if self._magerr is None:  # lazy load
            if self._data is None:  # lazy load from file
                self.load_data()
            self.calc_flux_mag()  # do this once, cache all the hidden variables
        return np.array(self._magerr)

    @hybrid_property
    def magref(self):
        """
        Reference magnitude, e.g.,
        the mean magnitude of a variable source,
        or the magnitude of a source before a transient started.
        This value is based on the ref_flux property.
        """
        if self.ref_flux is not None and self.ref_flux > 0:
            return -2.5 * np.log10(self.ref_flux) + PHOT_ZP
        else:
            return None

    @magref.setter
    def magref(self, magref):
        if magref is not None:
            self.ref_flux = 10 ** (-0.4 * (magref - PHOT_ZP))
        else:
            self.ref_flux = None

    @magref.expression
    def magref(cls):
        return sa.case(
            (
                sa.and_(
                    cls.ref_flux != None,  # noqa: E711
                    cls.ref_flux != 'NaN',
                    cls.ref_flux > 0,
                ),
                -2.5 * sa.func.log(cls.ref_flux) + PHOT_ZP,
            ),
            else_=None,
        )

    @hybrid_property
    def e_magref(self):
        """The error on the reference magnitude."""
        if (
            self.ref_flux is not None
            and self.ref_flux > 0
            and self.ref_fluxerr is not None
            and self.ref_fluxerr > 0
        ):
            return (2.5 / np.log(10)) * (self.ref_fluxerr / self.ref_flux)
        else:
            return None

    @e_magref.setter
    def e_magref(self, e_magref):
        if e_magref is not None:
            self.ref_fluxerr = e_magref * self.ref_flux / (2.5 / np.log(10))
        else:
            self.ref_fluxerr = None

    @e_magref.expression
    def e_magref(cls):
        """The error on the magnitude of the photometry point."""
        return sa.case(
            (
                sa.and_(
                    cls.ref_flux != None,  # noqa: E711
                    cls.ref_flux != 'NaN',
                    cls.ref_flux > 0,
                    cls.ref_fluxerr > 0,
                ),  # noqa: E711
                (2.5 / sa.func.ln(10)) * (cls.ref_fluxerr / cls.ref_flux),
            ),
            else_=None,
        )

    @property
    def magtot(self):
        """
        Total magnitude, e.g.,
        the combined magnitudes of a variable source,
        as opposed to the regular magnitudes which may come
        from subtraction images, etc.
        """
        if self.ref_flux is not None and self.ref_flux > 0:
            flux = self.fluxes
            bad_idx = np.isnan(flux) | (flux <= 0)
            flux[bad_idx] = 1
            mag = -2.5 * np.log10(self.ref_flux + flux) + PHOT_ZP
            mag[bad_idx] = np.nan
            return mag
        else:
            return None

    @property
    def e_magtot(self):
        """The error on the total magnitude."""
        if self.ref_flux is not None and self.ref_flux > 0 and self.ref_fluxerr > 0:
            flux = self.fluxes
            err = self.fluxerr
            bad_idx = np.isnan(flux) | np.isnan(err) | (flux <= 0) | (err <= 0)
            magerr = np.sqrt(err**2 + self.ref_fluxerr**2)
            magerr /= self.ref_flux + flux
            magerr *= 2.5 / np.log(10)
            magerr[bad_idx] = np.nan

            return magerr
        else:
            return None

    @property
    def tot_fluxes(self):
        """Total fluxes, e.g., the combined fluxes of a variable source."""
        if self.ref_flux is not None and self.ref_flux > 0:
            return self.ref_flux + self.fluxes
        else:
            return None

    @property
    def tot_fluxerr(self):
        """The errors on the total fluxes."""
        if self.ref_fluxerr is not None and self.ref_fluxerr > 0:
            err = self.fluxerr
            bad_idx = np.isnan(err) | (err <= 0)
            tot_err = np.sqrt(self.ref_fluxerr**2 + err**2)
            tot_err[bad_idx] = np.nan
            return tot_err
        else:
            return None

    @property
    def jd_first(self):
        """Julian Date of the first exposure of the series."""
        return self.mjd_first + 2_400_000.5

    @property
    def jd_mid(self):
        """Julian Date of the middle of the series."""
        return self.mjd_mid + 2_400_000.5

    @property
    def jd_last(self):
        """Julian Date of the last exposure of the series."""
        return self.mjd_last + 2_400_000.5

    @hybrid_property
    def iso_first(self):
        """UTC ISO timestamp (ArrowType) of the start of the series."""
        return arrow.get((self.mjd_first - 40_587) * 86400.0)

    @iso_first.expression
    def iso_first(cls):
        """UTC ISO timestamp (ArrowType) of the first exposure of the series."""
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_first - 40_587) * 86400.0)

    @hybrid_property
    def iso_mid(self):
        """UTC ISO timestamp (ArrowType) of the middle of the series."""
        return arrow.get((self.mjd_mid - 40_587) * 86400.0)

    @iso_mid.expression
    def iso_mid(cls):
        """UTC ISO timestamp (ArrowType) of the middle of the series."""
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_mid - 40_587) * 86400.0)

    @hybrid_property
    def iso_last(self):
        """UTC ISO timestamp (ArrowType) of the last exposure of the series."""
        return arrow.get((self.mjd_last - 40_587) * 86400.0)

    @iso_last.expression
    def iso_last(cls):
        """UTC ISO timestamp (ArrowType) of the last exposure of the series."""
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_last - 40_587) * 86400.0)

    @hybrid_property
    def iso_last_detected(self):
        """UTC ISO timestamp (ArrowType) of the last exposure of the series."""
        return arrow.get((self.mjd_last_detected - 40_587) * 86400.0)

    @iso_last_detected.expression
    def iso_last_detected(cls):
        """UTC ISO timestamp (ArrowType) of the last exposure of the series."""
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_last_detected - 40_587) * 86400.0)

    @property
    def snr(self):
        """Signal-to-noise ratio of each measurement"""
        average_flux = abs(np.nanmedian(self.fluxes))
        robust_flux_err = self.robust_rms * np.log(10) / 2.5 * average_flux
        if self.fluxerr is not None and np.all(self.fluxerr.shape == self.fluxes.shape):
            # assume the worst of the two errors:
            err = np.maximum(self.fluxerr, robust_flux_err)
            return self.fluxes / err

        return self.fluxes / robust_flux_err


PhotometricSeries.__table_args__ = (
    sa.Index(
        'phot_series_deduplication_index',
        PhotometricSeries.obj_id,
        PhotometricSeries.instrument_id,
        PhotometricSeries.origin,
        PhotometricSeries.filter,
        PhotometricSeries.series_name,
        PhotometricSeries.series_obj_id,
        PhotometricSeries.channel,
        unique=True,
    ),
)


@event.listens_for(PhotometricSeries, "before_insert")
def insert_new_dataset(mapper, connection, target):
    """
    This function is called before a new photometric series
    is inserted into the database. It checks that a file is
    associated with this object and raises a ValueError if not.
    """
    if target.filename is None:
        raise ValueError(
            "No filename specified for this PhotometricSeries. "
            "Save the data to disk to generate a filename. "
        )


@event.listens_for(PhotometricSeries, "after_delete")
def delete_dataset(mapper, connection, target):
    """
    This function is called after a PhotometricSeries
    is deleted from the database. If it is associated
    with a file, and it has autodelete=True, then
    the file will be automatically deleted.
    """
    if (
        target.autodelete
        and target.filename is not None
        and os.path.isfile(target.filename)
    ):
        os.remove(target.filename)
