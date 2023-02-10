import os
import time
import hashlib

import numpy as np
import pandas as pd

from skyportal.tests import api, assert_api, assert_api_fail


def test_hdf5_file_vs_memory_hash():
    df = pd.DataFrame(
        data=[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], columns=['a', 'b', 'c', 'd']
    )
    # open store without saving it to disk:
    # ref: https://github.com/pandas-dev/pandas/issues/9246#issuecomment-74041497
    with pd.HDFStore(
        'test_string', mode='w', driver="H5FD_CORE", driver_core_backing_store=0
    ) as store:
        store.put(
            'phot_series',
            df,
            format='table',
            index=None,
            track_times=False,
        )
        mem_buf = store._handle.get_file_image()
        mem_hash = hashlib.md5()
        mem_hash.update(mem_buf)

    # did not save the data to disk!
    assert not os.path.isfile('test_string')

    # make sure hashes saved at different times are the same
    time.sleep(1)

    # store the data on disk and check the hash of that
    filename = 'try_saving_hdf5_file_with_hash.h5'
    try:  # cleanup at end
        with pd.HDFStore(filename, mode='w') as store:
            store.put(
                'phot_series',
                df,
                format='table',
                index=None,
                track_times=False,
            )

        with open(filename, 'rb') as f:
            file_buf = f.read()
            file_hash = hashlib.md5()
            file_hash.update(file_buf)

        assert len(file_buf) == len(mem_buf)
        assert file_hash.hexdigest() == mem_hash.hexdigest()

        # make sure the same hash is made even when
        # changing the versions of pandas, etc.
        # if not, we will need to re-make all the hashes!
        assert file_hash.hexdigest() == 'daf70e10284a36020af2cc102ae3d32a'

    finally:
        if os.path.isfile(filename):
            os.remove(filename)


def test_post_retrieve_delete_series(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):

    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker(pandas=False)
        series_data = {
            'data': input_data,
            'obj_id': public_source.id,
            'instrument_id': ztf_camera.id,
            'ra': 234.22,
            'dec': 52.31,
            'series_name': '2020/summer',
            'series_obj_id': np.random.randint(1e3, 1e4),
            'exp_time': 30.0,
            'filter': 'ztfg',
            'origin': 'ZTF',
        }

        status, data = api(
            'POST',
            'photometric_series',
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]
        status, data = api(
            'GET',
            f'photometric_series/{ps_id}',
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data['data']['filename']
        output_data = data['data']['data']

        # make sure the data is the same
        assert input_data == output_data

        status, data = api(
            'DELETE',
            f'photometric_series/{ps_id}',
            token=upload_data_token,
        )
        assert_api(status, data)

        assert not os.path.isfile(filename)

    finally:

        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_post_illegal_data_series(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    input_data = {}
    series_data = {
        'data': input_data,
        'obj_id': public_source.id,
        'instrument_id': ztf_camera.id,
        'ra': 234.22,
        'dec': 52.31,
        'series_name': '2020/summer',
        'series_obj_id': np.random.randint(1e3, 1e4),
        'exp_time': 30.0,
        'filter': 'ztfg',
        'origin': 'ZTF',
    }
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Must supply a non-empty DataFrame.')

    input_data = phot_series_maker(pandas=False)
    input_data['mjddd'] = input_data.pop('mjd')
    series_data = {
        'data': input_data,
        'obj_id': public_source.id,
        'instrument_id': ztf_camera.id,
        'ra': 234.22,
        'dec': 52.31,
        'series_name': '2020/summer',
        'series_obj_id': np.random.randint(1e3, 1e4),
        'exp_time': 30.0,
        'filter': 'ztfg',
        'origin': 'ZTF',
    }
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Input to photometric series must contain')

    input_data['mjds'] = input_data.pop('mjddd')
    input_data['magggg'] = input_data.pop('mag')
    series_data = {
        'data': input_data,
        'obj_id': public_source.id,
        'instrument_id': ztf_camera.id,
        'ra': 234.22,
        'dec': 52.31,
        'series_name': '2020/summer',
        'series_obj_id': np.random.randint(1e3, 1e4),
        'exp_time': 30.0,
        'filter': 'ztfg',
        'origin': 'ZTF',
    }
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Input to photometric series must contain')


def test_post_bad_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    input_data = phot_series_maker(pandas=False)
    series_data = {
        'data': input_data,
    }
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Must supply an obj_id')

    # add the object id
    series_data.update({'obj_id': public_source.id})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Must supply an instrument_id')

    # add the instrument id (this number is not legal!)
    series_data.update({'instrument_id': 123456778})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Invalid instrument_id')

    # add the instrument id
    series_data.update({'instrument_id': ztf_camera.id})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(
        status,
        data,
        400,
        "The following keys are missing: "
        "['series_name', 'series_obj_id', 'ra', 'dec', 'exp_time', 'filter']",
    )

    # add the series name and obj_id
    series_data.update(
        {'series_name': 'test_series_id', 'series_obj_id': np.random.randint(1e3, 1e4)}
    )
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(
        status,
        data,
        400,
        "The following keys are missing: " "['ra', 'dec', 'exp_time', 'filter']",
    )

    # add everything else, but wrong filter
    series_data.update(
        {'ra': 234.22, 'dec': 52.31, 'exp_time': 30.0, 'filter': 'foobar'}
    )
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'is not allowed. Allowed filters are:')

    # filter is ok, but exp time is not a number
    series_data.update({'exp_time': 'foobar', 'filter': 'ztfg'})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Could not cast exp_time to the correct type')

    # try to add some optional metadata but with wrong values
    series_data.update({'exp_time': 30.0, 'magref': 'foobar'})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Could not cast magref to the correct type')

    series_data.update({'magref': 17.1, 'stream_ids': 'foobar'})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Invalid stream_ids parameter value')

    series_data.update({'stream_ids': [], 'altdata': 'foobar'})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Could not cast altdata to the correct type')

    series_data.update({'altdata': {}, 'followup_request_id': 123456789})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Invalid followup_request_id')
