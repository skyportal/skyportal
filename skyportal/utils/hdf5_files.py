import os
import uuid
import base64

import pandas as pd


def dump_dataframe_to_bytestream(df, metadata=None, keyname='phot_series', encode=True):
    """
    Convert a pandas dataframe to bytes.

    Parameters
    ----------
    df: pandas.DataFrame
        The dataframe to convert to bytes.
    metadata: dict
        A dictionary of metadata to store in the HDF5 file.
    keyname: str
        The keyname to store the dataframe under in the HDF5 file.
        Default is phot_series, to work with the PhotometricSeries tests.
    encode: bool
        Whether to encode the bytes as a base64 string.

    Returns
    -------
    bytes:
        The bytes of the dataframe.
        If encode=True, the bytes are encoded as a base64 string
        that can be sent over API calls.
        If encode=False, the bytes are the raw bytes of the HDF5 file.
    """

    filename = f"{uuid.uuid4().hex}.h5"  # generate a random filename

    # this store should work without writing to disk
    # if you open a regular store you'd just need
    # to delete the file at the end
    # ref: https://github.com/pandas-dev/pandas/issues/9246#issuecomment-74041497
    with pd.HDFStore(
        filename, mode='w', driver="H5FD_CORE", driver_core_backing_store=0
    ) as store:
        store.put(
            keyname,
            df,
            format='table',
            index=None,
            track_times=False,
        )
        if metadata is not None:
            store.get_storer(keyname).attrs.metadata = metadata

        data = store._handle.get_file_image()

        if encode:
            data = base64.b64encode(data)

    # should not be any file like this
    assert not os.path.isfile(filename)

    return data


def load_dataframe_from_bytestream(data):
    """
    Load the pandas data frame from a byte stream.
    Will return a DataFrame and a metadata dictionary,
    if such a dictionary is found in the data file's attributes.

    ref: https://github.com/pandas-dev/pandas/issues/9246#issuecomment-74041497
    """
    with pd.HDFStore(
        "data.h5",
        mode="r",
        driver="H5FD_CORE",
        driver_core_backing_store=0,
        driver_core_image=base64.b64decode(data),
    ) as store:
        keys = store.keys()
        if len(keys) != 1:
            raise ValueError(f'Expected 1 table in HDF5 file, got {len(keys)}. ')
        data = store[keys[0]]
        attributes = store.get_storer(keys[0]).attrs
        if 'metadata' in attributes and isinstance(attributes['metadata'], dict):
            metadata = attributes['metadata']
        else:
            metadata = {}

    return data, metadata
