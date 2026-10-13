import base64
import io
import os
import pickle
import uuid

import h5py
import numpy as np
import pandas as pd


class PickledObjectError(Exception):
    pass


SAFE_PICKLE_GLOBALS = {
    ("_codecs", "encode"),
    ("numpy", "dtype"),
    ("numpy", "ndarray"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy.core.multiarray", "scalar"),
    ("numpy.core.multiarray", "_reconstruct"),
}


class SafeGlobalsUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in SAFE_PICKLE_GLOBALS:
            return super().find_class(module, name)
        raise PickledObjectError(f"{module}.{name}")


def check_no_pickled_objects(image):
    def check_node(name, node):
        if "PSEUDOATOM" in node.attrs:
            raise ValueError(
                f'HDF5 node "{name}" stores pickled objects, '
                'save the DataFrame with format="table" instead.'
            )
        for value in node.attrs.values():
            for item in np.atleast_1d(value).ravel():
                if isinstance(item, str):
                    item = item.encode()
                if not isinstance(item, bytes):
                    continue
                for encoding in ("latin1", "bytes"):
                    try:
                        SafeGlobalsUnpickler(io.BytesIO(item), encoding=encoding).load()
                    except PickledObjectError as e:
                        raise ValueError(
                            f'HDF5 attribute on "{name}" contains a pickled {e}, '
                            "only plain Python and numpy values are allowed."
                        )
                    except Exception:
                        pass

    with h5py.File(io.BytesIO(image), "r") as f:
        check_node("/", f)
        f.visititems(check_node)


def dump_dataframe_to_bytestream(df, metadata=None, keyname="phot_series", encode=True):
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
        filename, mode="w", driver="H5FD_CORE", driver_core_backing_store=0
    ) as store:
        store.put(
            keyname,
            df,
            format="table",
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
    image = base64.b64decode(data)
    check_no_pickled_objects(image)
    with pd.HDFStore(
        "data.h5",
        mode="r",
        driver="H5FD_CORE",
        driver_core_backing_store=0,
        driver_core_image=image,
    ) as store:
        keys = store.keys()
        if len(keys) != 1:
            raise ValueError(f"Expected 1 table in HDF5 file, got {len(keys)}. ")
        data = store[keys[0]]
        attributes = store.get_storer(keys[0]).attrs
        if "metadata" in attributes and isinstance(attributes["metadata"], dict):
            metadata = attributes["metadata"]
        else:
            metadata = {}

    return data, metadata
