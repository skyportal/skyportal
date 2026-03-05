import hashlib
import os
import time
import uuid

import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa
from astropy.time import Time
from sqlalchemy.exc import IntegrityError

from skyportal.models import DBSession, PhotometricSeries
from skyportal.tests import api, assert_api, assert_api_fail
from skyportal.utils.hdf5_files import (
    dump_dataframe_to_bytestream,
    load_dataframe_from_bytestream,
)


def test_hdf5_file_vs_memory_hash():
    df = pd.DataFrame(
        data=[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], columns=["a", "b", "c", "d"]
    )
    mem_buf = dump_dataframe_to_bytestream(df, encode=False)
    mem_hash = hashlib.md5()
    mem_hash.update(mem_buf)

    # did not save the data to disk!
    assert not os.path.isfile("test_string")

    # make sure hashes saved at different times are the same
    time.sleep(1)

    # store the data on disk and check the hash of that
    filename = "try_saving_hdf5_file_with_hash.h5"
    try:  # cleanup at end
        with pd.HDFStore(filename, mode="w") as store:
            store.put(
                "phot_series",
                df,
                format="table",
                index=None,
                track_times=False,
            )

        with open(filename, "rb") as f:
            file_buf = f.read()
            file_hash = hashlib.md5()
            file_hash.update(file_buf)

        # assert len(file_buf) == len(mem_buf)
        assert file_hash.hexdigest() == mem_hash.hexdigest()

        # make sure the same hash is made even when
        # changing the versions of pandas, etc.
        # if not, we will need to re-make all the hashes!
        assert file_hash.hexdigest() == "daf70e10284a36020af2cc102ae3d32a"

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
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "ra": 234.22,
            "dec": 52.31,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
            "exp_time": 30.0,
            "filter": "ztfg",
            "origin": "ZTF",
        }

        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]
        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data["data"]["filename"]
        output_data = data["data"]["data"]

        # make sure the data is the same
        assert input_data == output_data

        status, data = api(
            "DELETE",
            f"photometric_series/{ps_id}",
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
        "data": input_data,
        "obj_id": public_source.id,
        "instrument_id": ztf_camera.id,
        "ra": 234.22,
        "dec": 52.31,
        "series_name": "2020/summer",
        "series_obj_id": np.random.randint(1e3, 1e4),
        "exp_time": 30.0,
        "filter": "ztfg",
        "origin": "ZTF",
    }
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Must supply a non-empty DataFrame.")

    input_data = phot_series_maker()
    input_data["mjddd"] = input_data.pop("mjd")
    series_data = {
        "data": input_data,
        "obj_id": public_source.id,
        "instrument_id": ztf_camera.id,
        "ra": 234.22,
        "dec": 52.31,
        "series_name": "2020/summer",
        "series_obj_id": np.random.randint(1e3, 1e4),
        "exp_time": 30.0,
        "filter": "ztfg",
        "origin": "ZTF",
    }
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Input to photometric series must contain")

    input_data["mjds"] = input_data.pop("mjddd")
    input_data["magggg"] = input_data.pop("mag")
    series_data = {
        "data": input_data,
        "obj_id": public_source.id,
        "instrument_id": ztf_camera.id,
        "ra": 234.22,
        "dec": 52.31,
        "series_name": "2020/summer",
        "series_obj_id": np.random.randint(1e3, 1e4),
        "exp_time": 30.0,
        "filter": "ztfg",
        "origin": "ZTF",
    }
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Input to photometric series must contain")


def test_post_bad_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    input_data = phot_series_maker()
    series_data = {
        "data": input_data,
    }
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Must supply an obj_id")

    # add the object id
    series_data.update({"obj_id": public_source.id})
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Must supply an instrument_id")

    # add the instrument id (this number is not legal!)
    series_data.update({"instrument_id": 123456778})
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Invalid instrument_id")

    # add the instrument id
    series_data.update({"instrument_id": ztf_camera.id})
    status, data = api(
        "POST",
        "photometric_series",
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
        {"series_name": "test_series_id", "series_obj_id": np.random.randint(1e3, 1e4)}
    )
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(
        status,
        data,
        400,
        "The following keys are missing: ['ra', 'dec', 'exp_time', 'filter']",
    )

    # add everything else, but wrong filter
    series_data.update(
        {"ra": 234.22, "dec": 52.31, "exp_time": 30.0, "filter": "foobar"}
    )
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "is not allowed. Allowed filters are:")

    # filter is ok, but exp time is not a number
    series_data.update({"exp_time": "foobar", "filter": "ztfg"})
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Could not cast exp_time to the correct type")

    # try to add some optional metadata but with wrong values
    series_data.update({"exp_time": 30.0, "magref": "foobar"})
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Could not cast magref to the correct type")

    series_data.update({"magref": 17.1, "stream_ids": "foobar"})
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Invalid stream_ids parameter value")

    series_data.update({"stream_ids": [], "altdata": "foobar"})
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Could not cast altdata to the correct type")

    series_data.update({"altdata": {}, "followup_request_id": 123456789})
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Invalid followup_request_id")

    series_data.pop("followup_request_id")
    series_data.update({"time_stamp_alignment": "foobar"})
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Allowed values are: start, middle, end")

    # add keywords that are not familiar
    series_data.update({"time_stamp_alignment": "middle", "foo": "bar"})
    status, data = api(
        "POST",
        "photometric_series",
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
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
        }
        status, data = api(
            "POST",
            "photometric_series",
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
        input_data = phot_series_maker(extra_columns=["ra", "dec"])
        assert "ra" in input_data
        assert "dec" in input_data

        series_data = {
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
        }
        status, data = api(
            "POST",
            "photometric_series",
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
        input_data = phot_series_maker(extra_columns=["ra", "dec", "exp_time"])
        assert "exp_time" in input_data

        series_data = {
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
        }
        status, data = api(
            "POST",
            "photometric_series",
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
            extra_columns=["ra", "dec", "exp_time", "filter"]
        )
        assert "filter" in input_data

        series_data = {
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
        }
        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data["data"]["filename"]
        output_data = data["data"]["data"]

        # make sure the data is the same
        assert input_data == output_data

        status, data = api(
            "DELETE",
            f"photometric_series/{ps_id}",
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
        byte_stream = dump_dataframe_to_bytestream(df)
        assert isinstance(byte_stream, bytes)

        series_data = {
            "data": byte_stream,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "ra": 234.22,
            "dec": 52.31,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
            "exp_time": 30.0,
            "filter": "ztfg",
            "origin": "ZTF",
        }

        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]
        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data["data"]["filename"]
        output_data = data["data"]["data"]

        # make sure the data is the same
        assert df.equals(pd.DataFrame(output_data))

        status, data = api(
            "DELETE",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)

        assert not os.path.isfile(filename)

    finally:
        if os.path.isfile("test_file.h5"):
            os.remove("test_file.h5")
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_post_dataframe_file_with_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker(
            ra=123, dec=-45.0, extra_columns=["ra", "dec", "exp_time", "filter"]
        )
        df = pd.DataFrame(input_data)

        metadata = {
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
        }
        byte_stream = dump_dataframe_to_bytestream(df, metadata)
        assert isinstance(byte_stream, bytes)

        series_data = {
            "data": byte_stream,
        }

        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]
        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data["data"]["filename"]
        output_data = data["data"]["data"]
        output_ra = data["data"]["ra"]
        output_dec = data["data"]["dec"]

        # make sure the data is the same
        assert df.equals(pd.DataFrame(output_data))
        assert abs(output_ra - 123) < 1e-3
        assert abs(output_dec + 45) < 1e-3

        status, data = api(
            "DELETE",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)

        assert not os.path.isfile(filename)

    finally:
        if os.path.isfile("test_file.h5"):
            os.remove("test_file.h5")
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_read_file_after_posting(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = {
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "ra": 123.22,
            "dec": -45.31,
            "series_name": "2022/winter",
            "series_obj_id": np.random.randint(1e3, 1e4),
            "exp_time": 30.0,
            "filter": "ztfg",
            "origin": "ZTF",
        }

        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]
        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data["data"]["filename"]
        output_data = data["data"]["data"]
        output_hash = data["data"]["hash"]

        # make sure the data is the same
        assert input_data == output_data

        assert os.path.isfile(filename)

        # now try to read the file's data and metadata
        with pd.HDFStore(filename, "r") as store:
            keys = list(store.keys())
            assert len(keys) == 1

            df = store[keys[0]]
            assert df.equals(pd.DataFrame(output_data))

            assert "metadata" in store.get_storer(keys[0]).attrs
            metadata = store.get_storer(keys[0]).attrs.metadata

        assert metadata["obj_id"] == public_source.id
        assert metadata["instrument_id"] == ztf_camera.id
        assert abs(metadata["ra"] - 123.22) < 1e-3
        assert abs(metadata["dec"] + 45.31) < 1e-3
        assert metadata["series_name"] == "2022/winter"
        assert metadata["series_obj_id"] == str(series_data["series_obj_id"])

        # check that the hash is the same!
        with open(filename, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        assert file_hash == output_hash

        status, data = api(
            "DELETE",
            f"photometric_series/{ps_id}",
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
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "ra": 234.22,
            "dec": 52.31,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
            "exp_time": 30.0,
            "filter": "ztfg",
            "origin": "ZTF",
        }

        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]
        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data["data"]["filename"]
        output_data = data["data"]["data"]

        # make sure the data is the same
        assert input_data == output_data

        # try to post the same data again
        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api_fail(status, data, 400, "already exists")

        # delete the file then try again
        os.remove(filename)

        # try to post the same data again
        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api_fail(
            status, data, 400, "A PhotometricSeries with the same hash already exists"
        )

        status, data = api(
            "DELETE",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)

        assert not os.path.isfile(filename)

    finally:
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_unique_constraint(phot_series_maker, user, public_source, ztf_camera):
    try:
        df = pd.DataFrame(phot_series_maker())
        filename = str(uuid.uuid4())
        series_obj_id = np.random.randint(1e3, 1e4)
        metadata = {
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "ra": 1.0,
            "dec": 1.0,
            "series_name": "dedup_test",
            "series_obj_id": series_obj_id,
            "exp_time": 30.0,
            "filter": "ztfg",
            "owner_id": user.id,
            "group_ids": [1],
            "stream_ids": [],
            "origin": "ZTF",
            "channel": 0,
        }
        session = DBSession()
        ps = PhotometricSeries(data=df, **metadata)
        ps.filename = filename
        original_hash = ps.hash
        session.add(ps)
        session.commit()

        # try to post the same data again
        metadata.update({"channel": 1})
        ps = PhotometricSeries(data=df, **metadata)
        ps.filename = str(uuid.uuid4())
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
        metadata.update({"channel": 0})  # same channel as original
        ps = PhotometricSeries(data=df, **metadata)
        ps.filename = str(uuid.uuid4())  # new filename
        ps.hash = str(uuid.uuid4())  # new hash
        session.add(ps)
        with pytest.raises(IntegrityError) as e:
            session.commit()

        assert 'violates unique constraint "phot_series_dedup' in str(e)
        session.rollback()

    finally:
        # make sure to cleanup:
        series = session.scalars(
            sa.select(PhotometricSeries).where(
                PhotometricSeries.series_name == "dedup_test"
            )
        ).all()
        [session.delete(s) for s in series]
        session.commit()


def test_autodelete_series(photometric_series):
    filename = photometric_series.filename
    assert os.path.isfile(filename)
    assert photometric_series.autodelete

    DBSession().delete(photometric_series)
    DBSession().commit()

    assert not os.path.isfile(filename)


def test_no_autodelete_series(photometric_series):
    filename = photometric_series.filename
    assert os.path.isfile(filename)
    photometric_series.autodelete = False

    DBSession().delete(photometric_series)
    DBSession().commit()

    assert os.path.isfile(filename)
    os.remove(filename)


def test_patch_series_data(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    filename = None
    ps_id = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = {
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "ra": 234.22,
            "dec": 52.31,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
            "exp_time": 30.0,
            "filter": "ztfg",
            "origin": "ZTF",
        }

        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        output_data = data["data"]["data"]

        # make sure the data is the same
        assert input_data == output_data

        # now change the data
        df = pd.DataFrame(input_data)

        new_df = df.copy()
        new_df["mjd"][3] += 1

        status, data = api(
            "PATCH",
            f"photometric_series/{ps_id}",
            data={"data": new_df.to_dict(orient="list")},
            token=upload_data_token,
        )
        assert_api(status, data)

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data["data"]["filename"]
        output_data = data["data"]["data"]

        # make sure the data is not the same
        assert input_data != output_data
        assert input_data["mjd"][3] == output_data["mjd"][3] - 1

    finally:
        if ps_id is not None:
            status, data = api(
                "DELETE",
                f"photometric_series/{ps_id}",
                token=upload_data_token,
            )
            assert_api(status, data)

        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_patch_series_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    filename = None
    ps_id = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = {
            "data": input_data,
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "ra": 234.22,
            "dec": 52.31,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
            "exp_time": 30.0,
            "filter": "ztfg",
            "origin": "ZTF",
        }

        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        filename = data["data"]["filename"]
        output_data = data["data"]["data"]

        # make sure the data is the same
        assert input_data == output_data

        # now change the metadata
        status, data = api(
            "PATCH",
            f"photometric_series/{ps_id}",
            data={"ra": series_data["ra"] + 1},
            token=upload_data_token,
        )
        assert_api(status, data)

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        output_metadata = data["data"]

        # make sure the data is not the same
        assert series_data != output_metadata
        assert series_data["ra"] == output_metadata["ra"] - 1

    finally:
        if ps_id is not None:
            status, data = api(
                "DELETE",
                f"photometric_series/{ps_id}",
                token=upload_data_token,
            )
            assert_api(status, data)

        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_patch_series_data_file_and_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    filename = None
    ps_id = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        metadata = {
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "ra": 234.22,
            "dec": 52.31,
            "series_name": "2020/summer",
            "series_obj_id": np.random.randint(1e3, 1e4),
            "exp_time": 30.0,
            "filter": "ztfg",
            "origin": "ZTF",
        }
        byte_data = dump_dataframe_to_bytestream(pd.DataFrame(input_data), metadata)
        series_data = {**metadata, "data": byte_data}

        status, data = api(
            "POST",
            "photometric_series",
            data=series_data,
            token=upload_data_token,
        )
        assert_api(status, data)
        ps_id = data["data"]["id"]

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)

        filename = data["data"]["filename"]
        output_data = data["data"]["data"]

        # make sure the data is the same
        assert input_data == output_data

        # now change the metadata
        metadata["dec"] += 1
        byte_data = dump_dataframe_to_bytestream(pd.DataFrame(input_data), metadata)

        status, data = api(
            "PATCH",
            f"photometric_series/{ps_id}",
            data={"data": byte_data},
            token=upload_data_token,
        )
        assert_api(status, data)

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        output_metadata = data["data"]

        # make sure the data is not the same
        assert series_data != output_metadata
        assert series_data["dec"] == output_metadata["dec"] - 1

        # now change the metadata, both in file and in direct input
        metadata["exp_time"] += 10
        byte_data = dump_dataframe_to_bytestream(pd.DataFrame(input_data), metadata)

        status, data = api(
            "PATCH",
            f"photometric_series/{ps_id}",
            data={"data": byte_data, "exp_time": 20},
            token=upload_data_token,
        )
        assert_api(status, data)

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        output_metadata = data["data"]

        # make sure the data is not the same
        assert series_data != output_metadata
        assert series_data["exp_time"] == output_metadata["exp_time"] + 10

        # now change the data to have different inferred values
        input_data["dec"] = np.ones(len(input_data["mjd"])) * 123.45
        # don't add any metadata:
        byte_data = dump_dataframe_to_bytestream(pd.DataFrame(input_data), {})

        status, data = api(
            "PATCH",
            f"photometric_series/{ps_id}",
            data={"data": byte_data},
            token=upload_data_token,
        )
        assert_api(status, data)

        status, data = api(
            "GET",
            f"photometric_series/{ps_id}",
            token=upload_data_token,
        )
        assert_api(status, data)
        output_metadata = data["data"]

        # make sure the data is not the same
        assert series_data != output_metadata
        assert output_metadata["dec"] == 123.45

    finally:
        if ps_id is not None:
            status, data = api(
                "DELETE",
                f"photometric_series/{ps_id}",
                token=upload_data_token,
            )
            assert_api(status, data)

        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_get_individual_series_by_id(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    filenames = []
    ps_ids = []
    raw_datasets = []
    ras = []
    decs = []
    filters = []
    object_ids = []
    inst_ids = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        filenames.append(ps.filename)
        ps_ids.append(ps.id)
        raw_datasets.append(ps.data)
        ras.append(ps.ra)
        decs.append(ps.dec)
        filters.append(ps.filter)
        object_ids.append(ps.obj_id)
        inst_ids.append(ps.instrument_id)

    # check that we can GET each PS on its own
    for i in range(3):
        status, data = api(
            "GET",
            f"photometric_series/{ps_ids[i]}",
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["filename"] == filenames[i]
        assert data["data"]["ra"] == ras[i]
        assert data["data"]["dec"] == decs[i]
        assert data["data"]["filter"] == filters[i]
        assert data["data"]["obj_id"] == object_ids[i]
        assert data["data"]["instrument_id"] == inst_ids[i]

    # check that we can GET all PSs at once
    status, data = api(
        "GET",
        "photometric_series",
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] >= 3
    assert len(data["data"]["series"]) >= 3
    assert set(ps_ids).issubset({ps["id"] for ps in data["data"]["series"]})


def test_get_series_cone_search(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ps_ids = []
    ras = []
    decs = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        ras.append(ps.ra)
        decs.append(ps.dec)

    # get each PS by its coordinates
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"ra": ras[i], "dec": decs[i], "radius": 2 / 3600},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]

        # will not find them if we fudge the coordinates
        new_dec = decs[i] + 0.1 if decs[i] < 0 else decs[i] - 0.1
        status, data = api(
            "GET",
            "photometric_series",
            params={"ra": ras[i], "dec": new_dec, "radius": 2 / 3600},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 0
        assert len(data["data"]["series"]) == 0


def test_get_series_by_filename(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    filenames = []
    ps_ids = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        filenames.append(ps.filename)
        ps_ids.append(ps.id)

    # filter by file name
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"filename": filenames[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]
        assert data["data"]["series"][0]["filename"] == filenames[i]


def test_get_series_by_object(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ps_ids = []
    object_ids = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        object_ids.append(ps.obj_id)

    # filter on full object IDs
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"objectID": object_ids[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]
        assert data["data"]["series"][0]["obj_id"] == object_ids[i]

    # check this works even with partial names:
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"objectID": object_ids[i][0:10]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]
        assert data["data"]["series"][0]["obj_id"] == object_ids[i]

    # now try to reject each object:
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"rejectedObjectID": object_ids[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] >= 2
        assert len(data["data"]["series"]) >= 2
        assert data["data"]["series"][0]["id"] != ps_ids[i]
        assert data["data"]["series"][0]["obj_id"] != object_ids[i]


def test_get_series_by_instrument_id(
    upload_data_token,
    photometric_series,
    photometric_series2,
    photometric_series3,
    ztf_camera,
    sedm,
):
    status, data = api(
        "GET",
        "photometric_series",
        params={"instrumentID": ztf_camera.id},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 2
    assert len(data["data"]["series"]) == 2
    assert all(ps["instrument_id"] == ztf_camera.id for ps in data["data"]["series"])
    assert photometric_series.id in [ps["id"] for ps in data["data"]["series"]]
    assert photometric_series2.id in [ps["id"] for ps in data["data"]["series"]]

    status, data = api(
        "GET",
        "photometric_series",
        params={"instrumentID": sedm.id},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 1
    assert len(data["data"]["series"]) == 1
    assert data["data"]["series"][0]["instrument_id"] == sedm.id
    assert data["data"]["series"][0]["id"] == photometric_series3.id


def test_get_series_by_name_and_obj_id(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ps_ids = []
    series_names = []
    series_obj_ids = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        series_names.append(ps.series_name)
        series_obj_ids.append(ps.series_obj_id)

    # filter series by series name
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"seriesName": series_names[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]
        assert data["data"]["series"][0]["series_name"] == series_names[i]

        # filter series by series obj id
        status, data = api(
            "GET",
            "photometric_series",
            params={"seriesObjID": series_obj_ids[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]
        assert data["data"]["series"][0]["series_obj_id"] == series_obj_ids[i]


def test_get_series_by_filter_origin_channel(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ps_ids = []
    filters = []
    origins = []
    channels = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        filters.append(ps.filter)
        origins.append(ps.origin)
        channels.append(ps.channel)

    # filter series by filter name
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"filter": filters[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]
        assert data["data"]["series"][0]["filter"] == filters[i]

    # filter series by origin
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"origin": origins[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]
        assert data["data"]["series"][0]["origin"] == origins[i]

    # filter series by channel (should get 1 or 2 each time)
    # because there are only channel A and B in the conftests!
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"channel": channels[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] <= 2
        assert len(data["data"]["series"]) <= 2
        assert ps_ids[i] in [ps["id"] for ps in data["data"]["series"]]
        assert all(channels[i] == ps["channel"] for ps in data["data"]["series"])


def test_get_series_start_mid_end_times(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ps_ids = []
    mjd_keys = ["first", "mid", "last"]
    time_keys = ["start", "mid", "end"]
    mjd_results = {}
    for k in mjd_keys:
        mjd_results[k] = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        for k in mjd_keys:
            mjd_results[k].append(getattr(ps, f"mjd_{k}"))

    for mk, tk in zip(mjd_keys, time_keys):
        values = mjd_results[mk].copy()
        values.sort()
        split_mjd = values[1]

        for op in ["Before", "After"]:
            if op == "Before":
                split_time = Time(split_mjd + 0.01, format="mjd").iso
            if op == "After":
                split_time = Time(split_mjd - 0.01, format="mjd").iso

            status, data = api(
                "GET",
                "photometric_series",
                params={f"{tk}{op}": split_time},
                token=upload_data_token,
            )
            assert_api(status, data)
            assert data["data"]["totalMatches"] == 2
            assert len(data["data"]["series"]) == 2
            if op == "Before":
                assert all(
                    ps[f"mjd_{mk}"] <= split_mjd for ps in data["data"]["series"]
                )
            if op == "After":
                assert all(
                    ps[f"mjd_{mk}"] >= split_mjd for ps in data["data"]["series"]
                )


def test_get_series_by_exposure_time(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ps_ids = []
    exptimes = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        exptimes.append(ps.exp_time)

    # see conftest.py
    assert exptimes == [30, 35, 25]

    # filter series by exposure time
    for i in range(3):
        status, data = api(
            "GET",
            "photometric_series",
            params={"expTime": exptimes[i]},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 1
        assert len(data["data"]["series"]) == 1
        assert data["data"]["series"][0]["id"] == ps_ids[i]
        assert data["data"]["series"][0]["exp_time"] == exptimes[i]

    # filter series by exposure time range
    for op in ["min", "max"]:
        status, data = api(
            "GET",
            "photometric_series",
            params={f"{op}ExpTime": 30},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 2
        assert len(data["data"]["series"]) == 2
        if op == "min":
            assert all(ps["exp_time"] >= 30 for ps in data["data"]["series"])
        if op == "max":
            assert all(ps["exp_time"] <= 30 for ps in data["data"]["series"])


def test_get_series_by_frame_rate(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ps_ids = []
    rates = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        rates.append(ps.frame_rate)

    values = rates.copy()
    values.sort()
    split_rate = values[1]

    # filter series by frame rate
    for op in ["min", "max"]:
        status, data = api(
            "GET",
            "photometric_series",
            params={f"{op}FrameRate": split_rate},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 2
        assert len(data["data"]["series"]) == 2
        if op == "min":
            assert all(ps["frame_rate"] >= split_rate for ps in data["data"]["series"])
        if op == "max":
            assert all(ps["frame_rate"] <= split_rate for ps in data["data"]["series"])


def test_get_series_by_num_exp(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ps_ids = []
    numbers = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        numbers.append(ps.num_exp)

    values = numbers.copy()
    values.sort()
    split_num = values[1]

    # filter series by frame rate
    for op in ["min", "max"]:
        status, data = api(
            "GET",
            "photometric_series",
            params={f"{op}NumExposures": split_num},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 2
        assert len(data["data"]["series"]) == 2
        if op == "min":
            assert all(ps["num_exp"] >= split_num for ps in data["data"]["series"])
        if op == "max":
            assert all(ps["num_exp"] <= split_num for ps in data["data"]["series"])


def test_get_series_by_mean_and_rms(
    upload_data_token,
    photometric_series_low_flux,
    photometric_series_low_flux_with_outliers,
    photometric_series_high_flux,
):
    ps_ids = []
    means = []
    rmses = []

    for ps in [
        photometric_series_low_flux,
        photometric_series_low_flux_with_outliers,
        photometric_series_high_flux,
    ]:
        ps_ids.append(ps.id)
        means.append(ps.mean_mag)
        rmses.append(ps.rms_mag)
    values = means.copy()
    values.sort()
    split_mag = values[1]

    # filter series by mean mag
    for op in ["Fainter", "Brighter"]:
        status, data = api(
            "GET",
            "photometric_series",
            params={f"mag{op}Than": split_mag},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 2
        assert len(data["data"]["series"]) == 2
        if op == "Fainter":
            assert all(ps["mean_mag"] >= split_mag for ps in data["data"]["series"])
        if op == "Brighter":
            assert all(ps["mean_mag"] <= split_mag for ps in data["data"]["series"])

    values = rmses.copy()
    values.sort()
    split_rms = values[1]

    # filter series by rms
    for op in ["min", "max"]:
        status, data = api(
            "GET",
            "photometric_series",
            params={f"{op}RMS": split_rms},
            token=upload_data_token,
        )
        assert_api(status, data)
        assert data["data"]["totalMatches"] == 2
        assert len(data["data"]["series"]) == 2
        if op == "min":
            assert all(ps["rms_mag"] >= split_rms for ps in data["data"]["series"])
        if op == "max":
            assert all(ps["rms_mag"] <= split_rms for ps in data["data"]["series"])


def test_get_series_by_robust_mean_mag(
    upload_data_token, photometric_series_low_flux_with_outliers
):
    ps = photometric_series_low_flux_with_outliers

    # make sure there is only one series with this name
    status, data = api(
        "GET",
        "photometric_series",
        params={"seriesName": "test_series_outliers"},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 1
    assert len(data["data"]["series"]) == 1
    assert data["data"]["series"][0]["id"] == ps.id

    # the mean magnitude is brighter because of outliers
    status, data = api(
        "GET",
        "photometric_series",
        params={
            "seriesName": "test_series_outliers",
            "magBrighterThan": ps.robust_mag - 0.01,
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 1
    assert len(data["data"]["series"]) == 1
    assert data["data"]["series"][0]["id"] == ps.id

    # searching for mean magnitude fainter than the mean mag
    status, data = api(
        "GET",
        "photometric_series",
        params={
            "seriesName": "test_series_outliers",
            "magBrighterThan": ps.mean_mag - 0.01,
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 0
    assert len(data["data"]["series"]) == 0

    # if we choose to measure by robust mean, we also get no results
    status, data = api(
        "GET",
        "photometric_series",
        params={
            "seriesName": "test_series_outliers",
            "magBrighterThan": ps.robust_mag - 0.01,
            "useRobustMagAndRMS": True,
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 0
    assert len(data["data"]["series"]) == 0


def test_get_series_by_robust_rms(
    upload_data_token, photometric_series_low_flux_with_outliers
):
    ps = photometric_series_low_flux_with_outliers

    # make sure there is only one series with this name
    status, data = api(
        "GET",
        "photometric_series",
        params={"seriesName": "test_series_outliers"},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 1
    assert len(data["data"]["series"]) == 1
    assert data["data"]["series"][0]["id"] == ps.id

    # the magnitude RMS is bigger because of outliers
    status, data = api(
        "GET",
        "photometric_series",
        params={
            "seriesName": "test_series_outliers",
            "minRMS": 0.4,
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 1
    assert len(data["data"]["series"]) == 1
    assert data["data"]["series"][0]["id"] == ps.id

    # searching for smaller RMS fails
    status, data = api(
        "GET",
        "photometric_series",
        params={
            "seriesName": "test_series_outliers",
            "maxRMS": 0.4,
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 0
    assert len(data["data"]["series"]) == 0

    # if choose to measure by robust mean, the results are reversed
    status, data = api(
        "GET",
        "photometric_series",
        params={
            "seriesName": "test_series_outliers",
            "minRMS": 0.4,
            "useRobustMagAndRMS": True,
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 0
    assert len(data["data"]["series"]) == 0

    # searching for smaller RMS now succeeds
    status, data = api(
        "GET",
        "photometric_series",
        params={
            "seriesName": "test_series_outliers",
            "maxRMS": 0.5,
            "useRobustMagAndRMS": True,
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 1
    assert len(data["data"]["series"]) == 1
    assert data["data"]["series"][0]["id"] == ps.id


def test_get_series_by_magref(
    upload_data_token,
    photometric_series,
    photometric_series2,
    photometric_series3,
    photometric_series_low_flux,
):
    assert photometric_series.magref == 18.1
    assert photometric_series2.magref == 19.2
    assert photometric_series3.magref == 20.3
    assert photometric_series_low_flux.magref is None

    # should retrieve first three series, not the low-flux one
    status, data = api(
        "GET",
        "photometric_series",
        params={"magrefFainterThan": 18.1},
        token=upload_data_token,
    )
    assert_api(status, data)

    assert data["data"]["totalMatches"] >= 3
    assert len(data["data"]["series"]) >= 3
    ids = [s["id"] for s in data["data"]["series"]]
    assert photometric_series.id in ids
    assert photometric_series2.id in ids
    assert photometric_series3.id in ids
    assert photometric_series_low_flux.id not in ids

    # the opposite:
    status, data = api(
        "GET",
        "photometric_series",
        params={"magrefBrighterThan": 18.1},
        token=upload_data_token,
    )
    assert_api(status, data)

    assert data["data"]["totalMatches"] >= 1
    assert len(data["data"]["series"]) >= 1
    ids = [s["id"] for s in data["data"]["series"]]
    assert photometric_series.id in ids
    assert photometric_series2.id not in ids
    assert photometric_series3.id not in ids
    assert photometric_series_low_flux.id not in ids

    # should retrieve last two series
    status, data = api(
        "GET",
        "photometric_series",
        params={"magrefFainterThan": 19.0},
        token=upload_data_token,
    )
    assert_api(status, data)

    assert data["data"]["totalMatches"] >= 2
    assert len(data["data"]["series"]) >= 2
    ids = [s["id"] for s in data["data"]["series"]]
    assert photometric_series.id not in ids
    assert photometric_series2.id in ids
    assert photometric_series3.id in ids
    assert photometric_series_low_flux.id not in ids

    # the opposite:
    status, data = api(
        "GET",
        "photometric_series",
        params={"magrefBrighterThan": 19.0},
        token=upload_data_token,
    )
    assert_api(status, data)

    assert data["data"]["totalMatches"] >= 1
    assert len(data["data"]["series"]) >= 1
    ids = [s["id"] for s in data["data"]["series"]]
    assert photometric_series.id in ids
    assert photometric_series2.id not in ids
    assert photometric_series3.id not in ids
    assert photometric_series_low_flux.id not in ids


def test_by_series_by_not_detected(
    upload_data_token, photometric_series_low_flux, photometric_series_undetected
):
    assert not photometric_series_undetected.is_detected

    status, data = api(
        "GET",
        "photometric_series",
        params={"detected": True},
        token=upload_data_token,
    )
    assert_api(status, data)

    assert data["data"]["totalMatches"] >= 1
    assert len(data["data"]["series"]) >= 1
    assert photometric_series_low_flux.id in [ps["id"] for ps in data["data"]["series"]]
    assert photometric_series_undetected.id not in [
        ps["id"] for ps in data["data"]["series"]
    ]

    status, data = api(
        "GET",
        "photometric_series",
        params={"detected": False},
        token=upload_data_token,
    )
    assert_api(status, data)

    assert data["data"]["totalMatches"] >= 1
    assert len(data["data"]["series"]) >= 1
    assert photometric_series_undetected.id in [
        ps["id"] for ps in data["data"]["series"]
    ]
    assert photometric_series_low_flux.id not in [
        ps["id"] for ps in data["data"]["series"]
    ]


def test_get_series_by_hash(upload_data_token, photometric_series):
    status, data = api(
        "GET",
        "photometric_series",
        params={"hash": photometric_series.hash},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] == 1
    assert len(data["data"]["series"]) == 1
    assert data["data"]["series"][0]["id"] == photometric_series.id


@pytest.mark.flaky(reruns=2)
def test_get_series_by_snr(
    upload_data_token,
    photometric_series_low_flux,
    photometric_series_low_flux_with_outliers,
    photometric_series_high_flux,
):
    ps_l = photometric_series_low_flux
    ps_h = photometric_series_high_flux
    ps_o = photometric_series_low_flux_with_outliers

    # low flux lightcurves should have SNR~5
    assert 5 < np.median(ps_l.snr) < 15
    assert 5 < np.median(ps_o.snr) < 15

    # high flux lightcurves should have SNR~100
    assert 50 < np.median(ps_h.snr) < 150

    # should get all three series:
    status, data = api(
        "GET",
        "photometric_series",
        params={"minMedianSNR": 5},
        token=upload_data_token,
    )

    assert_api(status, data)
    ids = [ps["id"] for ps in data["data"]["series"]]
    assert data["data"]["totalMatches"] >= 3
    assert ps_l.id in ids
    assert ps_h.id in ids
    assert ps_o.id in ids

    # should get none of the series:
    status, data = api(
        "GET",
        "photometric_series",
        params={"maxMedianSNR": 5},
        token=upload_data_token,
    )

    assert_api(status, data)
    ids = [ps["id"] for ps in data["data"]["series"]]
    assert ps_l.id not in ids
    assert ps_h.id not in ids
    assert ps_o.id not in ids

    # get only the series with the outlier with S/N=0
    status, data = api(
        "GET",
        "photometric_series",
        params={"maxWorstSNR": 0.1},
        token=upload_data_token,
    )

    assert_api(status, data)
    ids = [ps["id"] for ps in data["data"]["series"]]
    assert ps_l.id not in ids
    assert ps_h.id not in ids
    assert ps_o.id in ids

    # get the other two:
    status, data = api(
        "GET",
        "photometric_series",
        params={"minWorstSNR": 0.1},
        token=upload_data_token,
    )

    assert_api(status, data)
    ids = [ps["id"] for ps in data["data"]["series"]]
    assert ps_l.id in ids
    assert ps_h.id in ids
    assert ps_o.id not in ids

    # the best S/N will be the outliers and high-flux series
    status, data = api(
        "GET",
        "photometric_series",
        params={"minBestSNR": 100},
        token=upload_data_token,
    )

    assert_api(status, data)
    ids = [ps["id"] for ps in data["data"]["series"]]
    assert ps_l.id not in ids
    assert ps_h.id in ids
    assert ps_o.id in ids

    # the low-flux series doesn't have best S/N>100
    status, data = api(
        "GET",
        "photometric_series",
        params={"maxBestSNR": 100},
        token=upload_data_token,
    )

    assert_api(status, data)
    ids = [ps["id"] for ps in data["data"]["series"]]
    assert ps_l.id in ids
    assert ps_h.id not in ids
    assert ps_o.id not in ids


def test_get_series_sorting(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ids = [photometric_series.id, photometric_series2.id, photometric_series3.id]

    keys = [
        "id",
        "hash",
        "created_at",
        "ra",
        "dec",
        "mjd_first",
        "mjd_mid",
        "obj_id",
        "filter",
        "series_obj_id",
        "exp_time",
        "instrument_id",
        "mean_mag",
        "robust_rms",
        "median_snr",
        "best_snr",
        "owner_id",
    ]

    for key in keys:
        status, data = api(
            "GET",
            "photometric_series",
            params={"sortBy": key},
            token=upload_data_token,
        )

        assert_api(status, data)
        assert data["data"]["totalMatches"] >= 3
        series_list = data["data"]["series"]
        assert len(series_list) >= 3
        assert set(ids).issubset([ps["id"] for ps in series_list])
        for i in range(len(ids) - 1):
            assert series_list[i][key] <= series_list[i + 1][key]

        status, data = api(
            "GET",
            "photometric_series",
            params={"sortBy": key, "sortOrder": "desc"},
            token=upload_data_token,
        )

        assert_api(status, data)
        assert data["data"]["totalMatches"] >= 3
        series_list = data["data"]["series"]
        assert len(series_list) >= 3
        assert set(ids).issubset([ps["id"] for ps in series_list])
        for i in range(len(ids) - 1):
            assert series_list[i][key] >= series_list[i + 1][key]


def test_get_series_paged(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    ids = [photometric_series.id, photometric_series2.id, photometric_series3.id]

    # get all three series
    status, data = api(
        "GET",
        "photometric_series",
        token=upload_data_token,
    )

    assert_api(status, data)
    assert data["data"]["totalMatches"] >= 3
    assert len(data["data"]["series"]) >= 3
    assert set(ids).issubset([ps["id"] for ps in data["data"]["series"]])

    # get the first two series
    status, data = api(
        "GET",
        "photometric_series",
        params={"numPerPage": 2},
        token=upload_data_token,
    )

    assert_api(status, data)
    assert data["data"]["totalMatches"] >= 3
    assert len(data["data"]["series"]) == 2
    page1_ids = [ps["id"] for ps in data["data"]["series"]]

    # get the first two series
    status, data = api(
        "GET",
        "photometric_series",
        params={"numPerPage": 2, "pageNumber": 2},
        token=upload_data_token,
    )

    assert_api(status, data)
    assert data["data"]["totalMatches"] >= 3
    assert 1 <= len(data["data"]["series"]) <= 2
    page2_ids = [ps["id"] for ps in data["data"]["series"]]
    assert set(page1_ids).isdisjoint(page2_ids)


def test_download_formats_single_series(upload_data_token, photometric_series):
    # regular download of a single series
    status, data = api(
        "GET",
        f"photometric_series/{photometric_series.id}",
        params={},
        token=upload_data_token,
    )
    assert_api(status, data)

    ps1 = data["data"]
    assert photometric_series.series_name == ps1["series_name"]
    assert photometric_series.num_exp == ps1["num_exp"]
    assert isinstance(ps1["data"], dict)
    for key in ["mag", "mjd"]:
        assert key in ps1["data"]
        assert isinstance(ps1["data"][key], list)
        assert len(ps1["data"][key]) == ps1["num_exp"]

    # download of a single series using format='json'
    status, data = api(
        "GET",
        f"photometric_series/{photometric_series.id}",
        params={"dataFormat": "json"},
        token=upload_data_token,
    )
    assert_api(status, data)
    ps2 = data["data"]

    # the output should be the same as the default
    assert ps1 == ps2

    # download a single series using the HDF5 format
    status, data = api(
        "GET",
        f"photometric_series/{photometric_series.id}",
        params={"dataFormat": "hdf5"},
        token=upload_data_token,
    )
    assert_api(status, data)

    ps3 = data["data"]
    assert photometric_series.obj_id == ps3["obj_id"]
    assert photometric_series.num_exp == ps3["num_exp"]

    df, metadata = load_dataframe_from_bytestream(ps3["data"])

    assert isinstance(df, pd.DataFrame)
    assert isinstance(metadata, dict)

    # check the dataframe is consistent
    for key in ["mag", "mjd"]:
        assert key in df.columns
        assert df[key].to_list() == ps1["data"][key]

    # check (a random subset of the) metadata keys are consistent:
    for key in [
        "series_name",
        "obj_id",
        "owner_id",
        "filter",
        "ra",
        "dec",
        "ref_flux",
        "channel",
    ]:
        assert key in metadata
        assert metadata[key] == ps1[key]

        # download a single series using format='none'
        status, data = api(
            "GET",
            f"photometric_series/{photometric_series.id}",
            params={"dataFormat": "none"},
            token=upload_data_token,
        )
        assert_api(status, data)

        ps4 = data["data"]
        assert photometric_series.origin == ps4["origin"]
        assert photometric_series.num_exp == ps4["num_exp"]
        assert ps4["data"] is None

        # download a single series using wrong format='foobar'
        status, data = api(
            "GET",
            f"photometric_series/{photometric_series.id}",
            params={"dataFormat": "foobar"},
            token=upload_data_token,
        )
        assert_api_fail(status, data, 400, 'Invalid dataFormat: "foobar"')


def test_download_formats_multiple_series(
    upload_data_token, photometric_series, photometric_series2
):
    refs = [photometric_series, photometric_series2]

    # regular download of two series
    status, data = api(
        "GET",
        "photometric_series",
        params={},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] >= 2
    series = data["data"]["series"]
    assert len(series) >= 2

    for ref_ps in refs:
        for key in [
            "id",
            "filename",
            "ra",
            "dec",
            "filter",
            "origin",
            "num_exp",
            "series_name",
            "best_snr",
        ]:
            assert any(getattr(ref_ps, key) == ps[key] for ps in series)

    # by default, downloading multiple series does not return any data
    for ps in series:
        assert ps["data"] is None

    # download multiple series and specifying format='none' explicitly
    status, data = api(
        "GET",
        "photometric_series",
        params={"dataFormat": "none"},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] >= 2
    series = data["data"]["series"]
    assert len(series) >= 2

    for ref_ps in refs:
        for key in [
            "id",
            "filename",
            "ra",
            "dec",
            "filter",
            "origin",
            "num_exp",
            "series_name",
            "best_snr",
        ]:
            assert any(getattr(ref_ps, key) == ps[key] for ps in series)

    # downloading multiple series with format='none' does not return any data
    for ps in series:
        assert ps["data"] is None

    # download multiple series using format='json'
    status, data = api(
        "GET",
        "photometric_series",
        params={"dataFormat": "json"},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] >= 2
    series = data["data"]["series"]
    assert len(series) >= 2

    # first match each returned series dict to the reference series
    pairs = []
    for ref_ps in refs:
        for ps in series:
            if ref_ps.id == ps["id"]:
                pairs.append((ref_ps, ps))

    # check they are the same
    for ref_ps, ps in pairs:
        for key in [
            "id",
            "filename",
            "ra",
            "dec",
            "filter",
            "origin",
            "num_exp",
            "series_name",
            "best_snr",
        ]:
            assert getattr(ref_ps, key) == ps[key]

        # this time we should get the data as a dict of lists
        assert isinstance(ps["data"], dict)
        for key in ["mag", "mjd"]:
            assert key in ps["data"]
            assert isinstance(ps["data"][key], list)
            assert len(ps["data"][key]) == ps["num_exp"]
            assert ps["data"][key] == ref_ps.data[key].to_list()

    # download multiple series using the HDF5 format
    status, data = api(
        "GET",
        "photometric_series",
        params={"dataFormat": "hdf5"},
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["totalMatches"] >= 2
    series = data["data"]["series"]
    assert len(series) >= 2

    # first match each returned series dict to the reference series
    pairs = []
    for ref_ps in refs:
        for ps in series:
            if ref_ps.id == ps["id"]:
                pairs.append((ref_ps, ps))

    for ref_ps, ps in pairs:
        for key in [
            "id",
            "filename",
            "ra",
            "dec",
            "filter",
            "origin",
            "num_exp",
            "series_name",
            "best_snr",
        ]:
            assert getattr(ref_ps, key) == ps[key]

        # this time the data should be a bytestream convertible to dataframe
        df, metadata = load_dataframe_from_bytestream(ps["data"])

        assert isinstance(df, pd.DataFrame)
        assert isinstance(metadata, dict)

        # check the dataframe is consistent
        ref_ps.data.equals(df)

        # check (a random subset of the) metadata keys are consistent:
        for key in [
            "series_name",
            "obj_id",
            "owner_id",
            "filter",
            "ra",
            "dec",
            "ref_flux",
            "channel",
        ]:
            assert key in metadata
            assert metadata[key] == getattr(ref_ps, key)

    # download multiple series using wrong format='foobar'
    status, data = api(
        "GET",
        "photometric_series",
        params={"dataFormat": "foobar"},
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, 'Invalid dataFormat: "foobar"')
