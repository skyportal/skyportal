import base64

# import numpy as np
import pandas as pd

from baselayer.app.access import permissions  # , auth_or_token

# from baselayer.app.env import load_env
# from baselayer.log import make_log
from ..base import BaseHandler

# from .photometry import get_group_ids, get_stream_ids
from ...models.photometric_series import (
    REQUIRED_ATTRIBUTES,
    INFERABLE_ATTRIBUTES,
    OPTIONAL_ATTRIBUTES,
    DATA_TYPES,
)


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

    for colname in ['flux', 'fluxes', 'mags', 'magnitudes']:
        if colname not in data:
            raise KeyError(
                'Input to photometric series must contain '
                '"flux", "fluxes", "mags" or "magnitudes". '
            )
    if 'mjd' not in data and 'mjds' not in data:
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
        if key in data and len(data[key].unique()) == 0:
            metadata['filter'] = data[key][0]
            break


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
    for key in REQUIRED_ATTRIBUTES + INFERABLE_ATTRIBUTES:
        if key not in metadata:
            raise ValueError(f'"{key}" is a required attribute.')

    verified_metadata = {}
    for key in metadata.keys():
        if key not in REQUIRED_ATTRIBUTES + INFERABLE_ATTRIBUTES + OPTIONAL_ATTRIBUTES:
            raise ValueError(f'Unknown keyword argument "{key}"')
        # make sure each value can be cast to the correct type
        data_type = DATA_TYPES.get(key)
        if isinstance(data_type, str):
            verified_metadata[key] = str(metadata[key])
        elif isinstance(data_type, int):
            verified_metadata[key] = int(metadata[key])
        elif isinstance(data_type, float):
            verified_metadata[key] = float(metadata[key])
        elif isinstance(data_type, dict):
            verified_metadata[key] = dict(metadata[key])
        elif isinstance(data_type, list):
            verified_metadata[key] = list(metadata[key])
            if len(data_type) == 1:  # e.g., [int]
                verified_metadata[key] = [
                    data_type[0](v) for v in verified_metadata[key]
                ]
        # can add more types here if needed
        else:
            verified_metadata[key] = metadata[key]


class PhotometricSeriesHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---


        """
        json_data = self.get_json()
        data = json_data.pop('data')

        if data is None:
            return self.error(
                'Must supply data as a dictionary (JSON) or dataframe in HDF5 format. '
            )

        attributes_metadata = {}
        if isinstance(data, dict):
            try:
                data = pd.DataFrame(data)
            except Exception as e:
                return self.error(f'Could not convert data to a DataFrame. {e} ')
        elif isinstance(data, str):
            try:
                # load the pandas data frame from a byte stream:
                # ref: https://github.com/pandas-dev/pandas/issues/9246#issuecomment-74041497
                with pd.HDFStore(
                    "data.h5",
                    mode="r",
                    driver="H5FD_CORE",
                    driver_core_backing_store=0,
                    driver_core_image=base64.b64decode(data),
                ) as store:
                    keys = store.keys()
                    if len(keys) != 1:
                        return self.error(
                            f'Expected 1 table in HDF5 file, got {len(keys)}. '
                        )
                    data = store[keys[0]]
                    attributes = store.get_storer(keys[0]).attrs
                    if 'metadata' in attributes and isinstance(
                        attributes['metadata'], dict
                    ):
                        attributes_metadata = attributes['metadata']

            except Exception as e:
                return self.error(f'Could not load DataFrame from HDF5 file. {e} ')
        else:
            return self.error(
                'Data must be a dictionary (JSON) or dataframe in HDF5 format. '
            )

        try:
            # make sure data has the minimal columns:
            verify_data(data)

            # check if any metadata can be inferred from the data:
            metadata = infer_metadata(data)

            # if we got any more data from the HDF5 file:
            metadata.update(attributes_metadata)

            # now load any additional metadata from the json_data:
            metadata.update(json_data)

            # make sure all required attributes are present
            # make sure no unknown attributes are present
            verify_metadata(metadata)

        except Exception as e:
            return self.error(f'Problem parsing data/metadata. {e} ')

        print(data)
        print(metadata)
