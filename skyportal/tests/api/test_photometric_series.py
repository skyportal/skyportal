import os
import hashlib

import numpy as np
import pandas as pd


def test_hdf5_file_vs_memory_hash():
    df = pd.DataFrame(data=np.random.normal(size=(10, 3)), columns=['a', 'b', 'c'])
    # open store without saving it to disk:
    # ref: https://github.com/pandas-dev/pandas/issues/9246#issuecomment-74041497
    with pd.HDFStore(
        'test_string', mode='w', driver="H5FD_CORE", driver_core_backing_store=0
    ) as store:
        store.append('df', df)
        mem_buf = store._handle.get_file_image()
        mem_hash = hashlib.md5()
        mem_hash.update(mem_buf)

    # did not save the data to disk!
    assert not os.path.isfile('test_string')

    # store the data on disk and check the hash of that
    filename = 'try_saving_hdf5_file_with_hash.h5'
    try:  # cleanup at end
        with pd.HDFStore(filename, mode='w') as store:
            store.append('df', df)

        with open(filename, 'rb') as f:
            file_buf = f.read()
            file_hash = hashlib.md5()
            file_hash.update(file_buf)

        assert len(file_buf) == len(mem_buf)
        assert file_hash.hexdigest() == mem_hash.hexdigest()

    finally:
        if os.path.isfile(filename):
            os.remove(filename)
