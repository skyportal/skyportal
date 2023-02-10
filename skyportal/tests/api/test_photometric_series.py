import os
import time
import hashlib
import base64
import pytest
import uuid

import numpy as np
import pandas as pd

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from skyportal.tests import api, assert_api, assert_api_fail
from skyportal.models import DBSession, PhotometricSeries


def convert_dataframe_to_bytes(df, metadata=None):
    # this store should work without writing to disk
    # if you open a regular store you'd just need
    # to delete the file at the end
    # ref: https://github.com/pandas-dev/pandas/issues/9246#issuecomment-74041497
    with pd.HDFStore(
        'test_file.h5', mode='w', driver="H5FD_CORE", driver_core_backing_store=0
    ) as store:
        store.put(
            'phot_series',
            df,
            format='table',
            index=None,
            track_times=False,
        )
        if metadata is not None:
            store.get_storer('phot_series').attrs.metadata = metadata

        data = store._handle.get_file_image()
        data = base64.b64encode(data)

    # should not be any file like this
    assert not os.path.isfile('test_file.h5')

    return data


def test_hdf5_file_vs_memory_hash():
    df = pd.DataFrame(
        data=[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], columns=['a', 'b', 'c', 'd']
    )
    mem_buf = convert_dataframe_to_bytes(df)
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
        input_data = phot_series_maker()
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

    input_data = phot_series_maker()
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
    input_data = phot_series_maker()
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

    series_data.pop('followup_request_id')
    series_data.update({'time_stamp_alignment': 'foobar'})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Allowed values are: start, middle, end')

    # add keywords that are not familiar
    series_data.update({'time_stamp_alignment': 'middle', 'foo': 'bar'})
    status, data = api(
        'POST',
        'photometric_series',
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Unknown keys in metadata: ['foo']")


def test_post_inferred_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker(extra_columns=[])
        series_data = {
            'data': input_data,
            'obj_id': public_source.id,
            'instrument_id': ztf_camera.id,
            'series_name': '2020/summer',
            'series_obj_id': np.random.randint(1e3, 1e4),
        }
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
            "The following keys are missing: ['ra', 'dec', 'exp_time', 'filter']",
        )

        # should be able to get the RA/Dec from the data
        input_data = phot_series_maker(extra_columns=['ra', 'dec'])
        assert 'ra' in input_data
        assert 'dec' in input_data

        series_data = {
            'data': input_data,
            'obj_id': public_source.id,
            'instrument_id': ztf_camera.id,
            'series_name': '2020/summer',
            'series_obj_id': np.random.randint(1e3, 1e4),
        }
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
            "The following keys are missing: ['exp_time', 'filter']",
        )

        # should be able to get the exposure time, too
        input_data = phot_series_maker(extra_columns=['ra', 'dec', 'exp_time'])
        assert 'exp_time' in input_data

        series_data = {
            'data': input_data,
            'obj_id': public_source.id,
            'instrument_id': ztf_camera.id,
            'series_name': '2020/summer',
            'series_obj_id': np.random.randint(1e3, 1e4),
        }
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
            "The following keys are missing: ['filter']",
        )

        # should be able to get the exposure time, too
        input_data = phot_series_maker(
            extra_columns=['ra', 'dec', 'exp_time', 'filter']
        )
        assert 'filter' in input_data

        series_data = {
            'data': input_data,
            'obj_id': public_source.id,
            'instrument_id': ztf_camera.id,
            'series_name': '2020/summer',
            'series_obj_id': np.random.randint(1e3, 1e4),
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


def test_post_dataframe_file(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        df = pd.DataFrame(input_data)
        byte_stream = convert_dataframe_to_bytes(df)
        assert isinstance(byte_stream, bytes)

        series_data = {
            'data': byte_stream,
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
        assert df.equals(pd.DataFrame(output_data))

        status, data = api(
            'DELETE',
            f'photometric_series/{ps_id}',
            token=upload_data_token,
        )
        assert_api(status, data)

        assert not os.path.isfile(filename)

    finally:
        if os.path.isfile('test_file.h5'):
            os.remove('test_file.h5')
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_post_dataframe_file_with_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker(
            ra=123, dec=-45.0, extra_columns=['ra', 'dec', 'exp_time', 'filter']
        )
        df = pd.DataFrame(input_data)

        metadata = {
            'obj_id': public_source.id,
            'instrument_id': ztf_camera.id,
            'series_name': '2020/summer',
            'series_obj_id': np.random.randint(1e3, 1e4),
        }
        byte_stream = convert_dataframe_to_bytes(df, metadata)
        assert isinstance(byte_stream, bytes)

        series_data = {
            'data': byte_stream,
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
        output_ra = data["data"]["ra"]
        output_dec = data["data"]["dec"]

        # make sure the data is the same
        assert df.equals(pd.DataFrame(output_data))
        assert abs(output_ra - 123) < 1e-3
        assert abs(output_dec + 45) < 1e-3

        status, data = api(
            'DELETE',
            f'photometric_series/{ps_id}',
            token=upload_data_token,
        )
        assert_api(status, data)

        assert not os.path.isfile(filename)

    finally:
        if os.path.isfile('test_file.h5'):
            os.remove('test_file.h5')
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_read_file_after_posting(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):

    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = {
            'data': input_data,
            'obj_id': public_source.id,
            'instrument_id': ztf_camera.id,
            'ra': 123.22,
            'dec': -45.31,
            'series_name': '2022/winter',
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
        output_hash = data['data']['hash']

        # make sure the data is the same
        assert input_data == output_data

        assert os.path.isfile(filename)

        # now try to read the file's data and metadata
        with pd.HDFStore(filename, 'r') as store:
            keys = list(store.keys())
            assert len(keys) == 1

            df = store[keys[0]]
            assert df.equals(pd.DataFrame(output_data))

            assert 'metadata' in store.get_storer(keys[0]).attrs
            metadata = store.get_storer(keys[0]).attrs.metadata

        assert metadata['obj_id'] == public_source.id
        assert metadata['instrument_id'] == ztf_camera.id
        assert abs(metadata['ra'] - 123.22) < 1e-3
        assert abs(metadata['dec'] + 45.31) < 1e-3
        assert metadata['series_name'] == '2022/winter'
        assert metadata['series_obj_id'] == str(series_data['series_obj_id'])

        # check that the hash is the same!
        with open(filename, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        assert file_hash == output_hash

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


def test_cannot_repost_series(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):

    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
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

        # try to post the same data again
        status, data = api(
            'POST',
            'photometric_series',
            data=series_data,
            token=upload_data_token,
        )
        assert_api_fail(status, data, 400, 'File already exists:')

        # delete the file then try again
        os.remove(filename)

        # try to post the same data again
        status, data = api(
            'POST',
            'photometric_series',
            data=series_data,
            token=upload_data_token,
        )
        assert_api_fail(
            status, data, 400, 'A PhotometricSeries with the same hash already exists'
        )

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


def test_unique_constraint(phot_series_maker, user, public_source, ztf_camera):
    df = pd.DataFrame(phot_series_maker())
    filename = str(uuid.uuid4())
    series_obj_id = np.random.randint(1e3, 1e4)
    metadata = {
        'obj_id': public_source.id,
        'instrument_id': ztf_camera.id,
        'ra': 1.0,
        'dec': 1.0,
        'series_name': 'dedup_test',
        'series_obj_id': series_obj_id,
        'exp_time': 30.0,
        'filter': 'ztfg',
        'owner_id': user.id,
        'group_ids': [1],
        'stream_ids': [],
        'origin': 'ZTF',
        'channel': 0,
    }
    session = DBSession()
    ps = PhotometricSeries(data=df, **metadata)
    ps.filename = filename
    original_hash = ps.hash
    session.add(ps)
    session.commit()

    # try to post the same data again
    metadata.update({'channel': 1})
    ps = PhotometricSeries(data=df, **metadata)
    ps.filename = filename
    ps.hash = original_hash
    session.add(ps)
    with pytest.raises(IntegrityError) as e:
        session.commit()

    assert 'violates unique constraint "ix_photometric_series_hash"' in str(e)
    session.rollback()

    # try to post the same data but deliberately change the hash
    ps = PhotometricSeries(data=df, **metadata)
    ps.filename = filename
    ps.hash = str(uuid.uuid4())
    session.add(ps)
    with pytest.raises(IntegrityError) as e:
        session.commit()

    assert 'violates unique constraint "ix_photometric_series_filename"' in str(e)
    session.rollback()

    # try to post the same data and change both filename and hash
    # but make sure to go back to channel=0
    metadata.update({'channel': 0})
    ps = PhotometricSeries(data=df, **metadata)
    ps.filename = filename
    ps.hash = str(uuid.uuid4())
    session.add(ps)
    with pytest.raises(IntegrityError) as e:
        session.commit()

    assert 'violates unique constraint "phot_series_dedup' in str(e)
    session.rollback()

    # make sure to cleanup:
    series = session.scalars(
        sa.select(PhotometricSeries).where(
            PhotometricSeries.series_name == 'dedup_test'
        )
    ).all()
    [session.delete(s) for s in series]
    session.commit()
