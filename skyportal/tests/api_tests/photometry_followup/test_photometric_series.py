import hashlib
import os
import re
import time
import uuid

import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa
from astropy.time import Time
from skyportal_py import SkyPortalError
from skyportal_py.photometric_series import PhotometricSeriesPost
from sqlalchemy.exc import IntegrityError

from skyportal.models import DBSession, PhotometricSeries
from skyportal.tests import api, assert_api, assert_api_fail, client
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
    sp = client(upload_data_token)
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            ra=234.22,
            dec=52.31,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
            exp_time=30.0,
            filter="ztfg",
            origin="ZTF",
        )

        ps_id = sp.post_photometric_series(series_data).id
        ps = sp.fetch_photometric_series(ps_id)
        filename = ps.filename
        output_data = ps.data

        # make sure the data is the same
        assert input_data == output_data

        sp.delete_photometric_series(ps_id)

        assert not os.path.isfile(filename)

    finally:
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_post_illegal_data_series(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    sp = client(upload_data_token)
    input_data = {}
    series_data = PhotometricSeriesPost(
        data=input_data,
        obj_id=public_source.id,
        instrument_id=ztf_camera.id,
        ra=234.22,
        dec=52.31,
        series_name="2020/summer",
        series_obj_id=str(np.random.randint(1e3, 1e4)),
        exp_time=30.0,
        filter="ztfg",
        origin="ZTF",
    )
    with pytest.raises(
        SkyPortalError, match=re.escape("Must supply a non-empty DataFrame.")
    ) as err:
        sp.post_photometric_series(series_data)
    assert err.value.status_code == 400

    input_data = phot_series_maker()
    input_data["mjddd"] = input_data.pop("mjd")
    series_data = PhotometricSeriesPost(
        data=input_data,
        obj_id=public_source.id,
        instrument_id=ztf_camera.id,
        ra=234.22,
        dec=52.31,
        series_name="2020/summer",
        series_obj_id=str(np.random.randint(1e3, 1e4)),
        exp_time=30.0,
        filter="ztfg",
        origin="ZTF",
    )
    with pytest.raises(
        SkyPortalError, match="Input to photometric series must contain"
    ) as err:
        sp.post_photometric_series(series_data)
    assert err.value.status_code == 400

    input_data["mjds"] = input_data.pop("mjddd")
    input_data["magggg"] = input_data.pop("mag")
    series_data = PhotometricSeriesPost(
        data=input_data,
        obj_id=public_source.id,
        instrument_id=ztf_camera.id,
        ra=234.22,
        dec=52.31,
        series_name="2020/summer",
        series_obj_id=str(np.random.randint(1e3, 1e4)),
        exp_time=30.0,
        filter="ztfg",
        origin="ZTF",
    )
    with pytest.raises(
        SkyPortalError, match="Input to photometric series must contain"
    ) as err:
        sp.post_photometric_series(series_data)
    assert err.value.status_code == 400


def test_post_bad_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    sp = client(upload_data_token)
    input_data = phot_series_maker()
    series_data = {
        "data": input_data,
    }
    with pytest.raises(SkyPortalError, match="Must supply an obj_id") as err:
        sp.post_photometric_series(PhotometricSeriesPost(**series_data))
    assert err.value.status_code == 400

    # add the object id
    series_data.update({"obj_id": public_source.id})
    with pytest.raises(SkyPortalError, match="Must supply an instrument_id") as err:
        sp.post_photometric_series(PhotometricSeriesPost(**series_data))
    assert err.value.status_code == 400

    # add the instrument id (this number is not legal!)
    series_data.update({"instrument_id": 123456778})
    with pytest.raises(SkyPortalError, match="Invalid instrument_id") as err:
        sp.post_photometric_series(PhotometricSeriesPost(**series_data))
    assert err.value.status_code == 400

    # add the instrument id
    series_data.update({"instrument_id": ztf_camera.id})
    with pytest.raises(
        SkyPortalError,
        match=re.escape(
            "The following keys are missing: "
            "['series_name', 'series_obj_id', 'ra', 'dec', 'exp_time', 'filter']"
        ),
    ) as err:
        sp.post_photometric_series(PhotometricSeriesPost(**series_data))
    assert err.value.status_code == 400

    # add the series name and obj_id
    series_data.update(
        {
            "series_name": "test_series_id",
            "series_obj_id": str(np.random.randint(1e3, 1e4)),
        }
    )
    with pytest.raises(
        SkyPortalError,
        match=re.escape(
            "The following keys are missing: ['ra', 'dec', 'exp_time', 'filter']"
        ),
    ) as err:
        sp.post_photometric_series(PhotometricSeriesPost(**series_data))
    assert err.value.status_code == 400

    # add everything else, but wrong filter
    series_data.update(
        {"ra": 234.22, "dec": 52.31, "exp_time": 30.0, "filter": "foobar"}
    )
    with pytest.raises(
        SkyPortalError, match=re.escape("is not allowed. Allowed filters are:")
    ) as err:
        sp.post_photometric_series(PhotometricSeriesPost(**series_data))
    assert err.value.status_code == 400

    # filter is ok, but exp time is not a number
    series_data.update({"exp_time": "foobar", "filter": "ztfg"})
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Could not cast exp_time to the correct type")

    # try to add some optional metadata but with wrong values
    series_data.update({"exp_time": 30.0, "magref": "foobar"})
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Could not cast magref to the correct type")

    series_data.update({"magref": 17.1, "stream_ids": "foobar"})
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Invalid stream_ids parameter value")

    series_data.update({"stream_ids": [], "altdata": "foobar"})
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Could not cast altdata to the correct type")

    series_data.update({"altdata": {}, "followup_request_id": 123456789})
    with pytest.raises(SkyPortalError, match="Invalid followup_request_id") as err:
        sp.post_photometric_series(PhotometricSeriesPost(**series_data))
    assert err.value.status_code == 400

    series_data.pop("followup_request_id")
    series_data.update({"time_stamp_alignment": "foobar"})
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometric_series",
        data=series_data,
        token=upload_data_token,
    )
    assert_api_fail(status, data, 400, "Allowed values are: start, middle, end")

    # add keywords that are not familiar
    series_data.update({"time_stamp_alignment": "middle", "foo": "bar"})
    # raw api: intentionally malformed payload the typed client can't produce
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
    sp = client(upload_data_token)
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker(extra_columns=[])
        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
        )
        with pytest.raises(
            SkyPortalError,
            match=re.escape(
                "The following keys are missing: ['ra', 'dec', 'exp_time', 'filter']"
            ),
        ) as err:
            sp.post_photometric_series(series_data)
        assert err.value.status_code == 400

        # should be able to get the RA/Dec from the data
        input_data = phot_series_maker(extra_columns=["ra", "dec"])
        assert "ra" in input_data
        assert "dec" in input_data

        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
        )
        with pytest.raises(
            SkyPortalError,
            match=re.escape("The following keys are missing: ['exp_time', 'filter']"),
        ) as err:
            sp.post_photometric_series(series_data)
        assert err.value.status_code == 400

        # should be able to get the exposure time, too
        input_data = phot_series_maker(extra_columns=["ra", "dec", "exp_time"])
        assert "exp_time" in input_data

        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
        )
        with pytest.raises(
            SkyPortalError,
            match=re.escape("The following keys are missing: ['filter']"),
        ) as err:
            sp.post_photometric_series(series_data)
        assert err.value.status_code == 400

        # should be able to get the exposure time, too
        input_data = phot_series_maker(
            extra_columns=["ra", "dec", "exp_time", "filter"]
        )
        assert "filter" in input_data

        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
        )
        ps_id = sp.post_photometric_series(series_data).id

        ps = sp.fetch_photometric_series(ps_id)
        filename = ps.filename
        output_data = ps.data

        # make sure the data is the same
        assert input_data == output_data

        sp.delete_photometric_series(ps_id)

        assert not os.path.isfile(filename)

    finally:
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_post_dataframe_file(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    sp = client(upload_data_token)
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        df = pd.DataFrame(input_data)
        byte_stream = dump_dataframe_to_bytestream(df)
        assert isinstance(byte_stream, bytes)

        series_data = PhotometricSeriesPost(
            data=byte_stream,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            ra=234.22,
            dec=52.31,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
            exp_time=30.0,
            filter="ztfg",
            origin="ZTF",
        )

        ps_id = sp.post_photometric_series(series_data).id
        ps = sp.fetch_photometric_series(ps_id)
        filename = ps.filename
        output_data = ps.data

        # make sure the data is the same
        assert df.equals(pd.DataFrame(output_data))

        sp.delete_photometric_series(ps_id)

        assert not os.path.isfile(filename)

    finally:
        if os.path.isfile("test_file.h5"):
            os.remove("test_file.h5")
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_post_dataframe_file_with_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    sp = client(upload_data_token)
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

        series_data = PhotometricSeriesPost(
            data=byte_stream,
        )

        ps_id = sp.post_photometric_series(series_data).id
        ps = sp.fetch_photometric_series(ps_id)
        filename = ps.filename
        output_data = ps.data
        output_ra = ps.ra
        output_dec = ps.dec

        # make sure the data is the same
        assert df.equals(pd.DataFrame(output_data))
        assert abs(output_ra - 123) < 1e-3
        assert abs(output_dec + 45) < 1e-3

        sp.delete_photometric_series(ps_id)

        assert not os.path.isfile(filename)

    finally:
        if os.path.isfile("test_file.h5"):
            os.remove("test_file.h5")
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_read_file_after_posting(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    sp = client(upload_data_token)
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            ra=123.22,
            dec=-45.31,
            series_name="2022/winter",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
            exp_time=30.0,
            filter="ztfg",
            origin="ZTF",
        )

        ps_id = sp.post_photometric_series(series_data).id
        ps = sp.fetch_photometric_series(ps_id)
        filename = ps.filename
        output_data = ps.data
        output_hash = ps.hash

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
        assert metadata["series_obj_id"] == series_data.series_obj_id

        # check that the hash is the same!
        with open(filename, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        assert file_hash == output_hash

        sp.delete_photometric_series(ps_id)

        assert not os.path.isfile(filename)

    finally:
        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_cannot_repost_series(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    sp = client(upload_data_token)
    filename = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            ra=234.22,
            dec=52.31,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
            exp_time=30.0,
            filter="ztfg",
            origin="ZTF",
        )

        ps_id = sp.post_photometric_series(series_data).id
        ps = sp.fetch_photometric_series(ps_id)
        filename = ps.filename
        output_data = ps.data

        # make sure the data is the same
        assert input_data == output_data

        # try to post the same data again
        with pytest.raises(SkyPortalError, match="already exists") as err:
            sp.post_photometric_series(series_data)
        assert err.value.status_code == 400

        # delete the file then try again
        os.remove(filename)

        # try to post the same data again
        with pytest.raises(
            SkyPortalError,
            match="A PhotometricSeries with the same hash already exists",
        ) as err:
            sp.post_photometric_series(series_data)
        assert err.value.status_code == 400

        sp.delete_photometric_series(ps_id)

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
    sp = client(upload_data_token)
    filename = None
    ps_id = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            ra=234.22,
            dec=52.31,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
            exp_time=30.0,
            filter="ztfg",
            origin="ZTF",
        )

        ps_id = sp.post_photometric_series(series_data).id

        output_data = sp.fetch_photometric_series(ps_id).data

        # make sure the data is the same
        assert input_data == output_data

        # now change the data
        df = pd.DataFrame(input_data)

        new_df = df.copy()
        # Use .loc (not chained `new_df["mjd"][3]`) so the edit lands on new_df:
        # chained assignment writes to a temporary copy and raises under
        # pandas >= 3.0's Copy-on-Write, leaving the data unchanged.
        new_df.loc[3, "mjd"] += 1

        sp.update_photometric_series(
            ps_id, PhotometricSeriesPost(data=new_df.to_dict(orient="list"))
        )

        ps = sp.fetch_photometric_series(ps_id)
        filename = ps.filename
        output_data = ps.data

        # make sure the data is not the same
        assert input_data != output_data
        assert input_data["mjd"][3] == output_data["mjd"][3] - 1

    finally:
        if ps_id is not None:
            sp.delete_photometric_series(ps_id)

        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_patch_series_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    sp = client(upload_data_token)
    filename = None
    ps_id = None

    try:  # cleanup file at the end
        input_data = phot_series_maker()
        series_data = PhotometricSeriesPost(
            data=input_data,
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            ra=234.22,
            dec=52.31,
            series_name="2020/summer",
            series_obj_id=str(np.random.randint(1e3, 1e4)),
            exp_time=30.0,
            filter="ztfg",
            origin="ZTF",
        )

        ps_id = sp.post_photometric_series(series_data).id

        ps = sp.fetch_photometric_series(ps_id)
        filename = ps.filename
        output_data = ps.data

        # make sure the data is the same
        assert input_data == output_data

        # now change the metadata
        sp.update_photometric_series(
            ps_id, PhotometricSeriesPost(ra=series_data.ra + 1)
        )

        output_metadata = sp.fetch_photometric_series(ps_id)

        # make sure the data is not the same
        assert series_data != output_metadata
        assert series_data.ra == output_metadata.ra - 1

    finally:
        if ps_id is not None:
            sp.delete_photometric_series(ps_id)

        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_patch_series_data_file_and_metadata(
    phot_series_maker, upload_data_token, public_source, ztf_camera
):
    sp = client(upload_data_token)
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
            "series_obj_id": str(np.random.randint(1e3, 1e4)),
            "exp_time": 30.0,
            "filter": "ztfg",
            "origin": "ZTF",
        }
        byte_data = dump_dataframe_to_bytestream(pd.DataFrame(input_data), metadata)
        series_data = PhotometricSeriesPost(**metadata, data=byte_data)

        ps_id = sp.post_photometric_series(series_data).id

        ps = sp.fetch_photometric_series(ps_id)

        filename = ps.filename
        output_data = ps.data

        # make sure the data is the same
        assert input_data == output_data

        # now change the metadata
        metadata["dec"] += 1
        byte_data = dump_dataframe_to_bytestream(pd.DataFrame(input_data), metadata)

        sp.update_photometric_series(ps_id, PhotometricSeriesPost(data=byte_data))

        output_metadata = sp.fetch_photometric_series(ps_id)

        # make sure the data is not the same
        assert series_data != output_metadata
        assert series_data.dec == output_metadata.dec - 1

        # now change the metadata, both in file and in direct input
        metadata["exp_time"] += 10
        byte_data = dump_dataframe_to_bytestream(pd.DataFrame(input_data), metadata)

        sp.update_photometric_series(
            ps_id, PhotometricSeriesPost(data=byte_data, exp_time=20)
        )

        output_metadata = sp.fetch_photometric_series(ps_id)

        # make sure the data is not the same
        assert series_data != output_metadata
        assert series_data.exp_time == output_metadata.exp_time + 10

        # now change the data to have different inferred values
        input_data["dec"] = np.ones(len(input_data["mjd"])) * 123.45
        # don't add any metadata:
        byte_data = dump_dataframe_to_bytestream(pd.DataFrame(input_data), {})

        sp.update_photometric_series(ps_id, PhotometricSeriesPost(data=byte_data))

        output_metadata = sp.fetch_photometric_series(ps_id)

        # make sure the data is not the same
        assert series_data != output_metadata
        assert output_metadata.dec == 123.45

    finally:
        if ps_id is not None:
            sp.delete_photometric_series(ps_id)

        if filename is not None and os.path.isfile(filename):
            os.remove(filename)


def test_get_individual_series_by_id(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
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
        ps_data = sp.fetch_photometric_series(ps_ids[i])
        assert ps_data.filename == filenames[i]
        assert ps_data.ra == ras[i]
        assert ps_data.dec == decs[i]
        assert ps_data.filter == filters[i]
        assert ps_data.obj_id == object_ids[i]
        assert ps_data.instrument_id == inst_ids[i]

    # check that we can GET all PSs at once
    page = sp.fetch_photometric_series_page()
    assert page.total_matches >= 3
    assert len(page.series) >= 3
    assert set(ps_ids).issubset({ps.id for ps in page.series})


def test_get_series_cone_search(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
    ps_ids = []
    ras = []
    decs = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        ras.append(ps.ra)
        decs.append(ps.dec)

    # get each PS by its coordinates
    for i in range(3):
        page = sp.fetch_photometric_series_page(ra=ras[i], dec=decs[i], radius=2 / 3600)
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]

        # will not find them if we fudge the coordinates
        new_dec = decs[i] + 0.1 if decs[i] < 0 else decs[i] - 0.1
        page = sp.fetch_photometric_series_page(ra=ras[i], dec=new_dec, radius=2 / 3600)
        assert page.total_matches == 0
        assert len(page.series) == 0


def test_get_series_by_filename(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
    filenames = []
    ps_ids = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        filenames.append(ps.filename)
        ps_ids.append(ps.id)

    # filter by file name
    for i in range(3):
        page = sp.fetch_photometric_series_page(filename=filenames[i])
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]
        assert page.series[0].filename == filenames[i]


def test_get_series_by_object(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
    ps_ids = []
    object_ids = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        object_ids.append(ps.obj_id)

    # filter on full object IDs
    for i in range(3):
        page = sp.fetch_photometric_series_page(object_id=object_ids[i])
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]
        assert page.series[0].obj_id == object_ids[i]

    # check this works even with partial names:
    for i in range(3):
        page = sp.fetch_photometric_series_page(object_id=object_ids[i][0:10])
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]
        assert page.series[0].obj_id == object_ids[i]

    # now try to reject each object:
    for i in range(3):
        page = sp.fetch_photometric_series_page(rejected_object_id=object_ids[i])
        assert page.total_matches >= 2
        assert len(page.series) >= 2
        assert page.series[0].id != ps_ids[i]
        assert page.series[0].obj_id != object_ids[i]


def test_get_series_by_instrument_id(
    upload_data_token,
    photometric_series,
    photometric_series2,
    photometric_series3,
    ztf_camera,
    sedm,
):
    sp = client(upload_data_token)
    page = sp.fetch_photometric_series_page(instrument_id=ztf_camera.id)
    assert page.total_matches == 2
    assert len(page.series) == 2
    assert all(ps.instrument_id == ztf_camera.id for ps in page.series)
    assert photometric_series.id in [ps.id for ps in page.series]
    assert photometric_series2.id in [ps.id for ps in page.series]

    page = sp.fetch_photometric_series_page(instrument_id=sedm.id)
    assert page.total_matches == 1
    assert len(page.series) == 1
    assert page.series[0].instrument_id == sedm.id
    assert page.series[0].id == photometric_series3.id


def test_get_series_by_name_and_obj_id(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
    ps_ids = []
    series_names = []
    series_obj_ids = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        series_names.append(ps.series_name)
        series_obj_ids.append(ps.series_obj_id)

    # filter series by series name
    for i in range(3):
        page = sp.fetch_photometric_series_page(series_name=series_names[i])
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]
        assert page.series[0].series_name == series_names[i]

        # filter series by series obj id
        page = sp.fetch_photometric_series_page(series_obj_id=series_obj_ids[i])
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]
        assert page.series[0].series_obj_id == series_obj_ids[i]


def test_get_series_by_filter_origin_channel(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
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
        page = sp.fetch_photometric_series_page(filter=filters[i])
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]
        assert page.series[0].filter == filters[i]

    # filter series by origin
    for i in range(3):
        page = sp.fetch_photometric_series_page(origin=origins[i])
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]
        assert page.series[0].origin == origins[i]

    # filter series by channel (should get 1 or 2 each time)
    # because there are only channel A and B in the conftests!
    for i in range(3):
        page = sp.fetch_photometric_series_page(channel=channels[i])
        assert page.total_matches <= 2
        assert len(page.series) <= 2
        assert ps_ids[i] in [ps.id for ps in page.series]
        assert all(channels[i] == ps.channel for ps in page.series)


def test_get_series_start_mid_end_times(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
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

            page = sp.fetch_photometric_series_page(
                **{f"{tk}_{op.lower()}": split_time}
            )
            assert page.total_matches == 2
            assert len(page.series) == 2
            if op == "Before":
                assert all(getattr(ps, f"mjd_{mk}") <= split_mjd for ps in page.series)
            if op == "After":
                assert all(getattr(ps, f"mjd_{mk}") >= split_mjd for ps in page.series)


def test_get_series_by_exposure_time(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
    ps_ids = []
    exptimes = []

    for ps in [photometric_series, photometric_series2, photometric_series3]:
        ps_ids.append(ps.id)
        exptimes.append(ps.exp_time)

    # see conftest.py
    assert exptimes == [30, 35, 25]

    # filter series by exposure time
    for i in range(3):
        page = sp.fetch_photometric_series_page(exp_time=exptimes[i])
        assert page.total_matches == 1
        assert len(page.series) == 1
        assert page.series[0].id == ps_ids[i]
        assert page.series[0].exp_time == exptimes[i]

    # filter series by exposure time range
    for op in ["min", "max"]:
        page = sp.fetch_photometric_series_page(**{f"{op}_exp_time": 30})
        assert page.total_matches == 2
        assert len(page.series) == 2
        if op == "min":
            assert all(ps.exp_time >= 30 for ps in page.series)
        if op == "max":
            assert all(ps.exp_time <= 30 for ps in page.series)


def test_get_series_by_frame_rate(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
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
        page = sp.fetch_photometric_series_page(**{f"{op}_frame_rate": split_rate})
        assert page.total_matches == 2
        assert len(page.series) == 2
        if op == "min":
            assert all(ps.frame_rate >= split_rate for ps in page.series)
        if op == "max":
            assert all(ps.frame_rate <= split_rate for ps in page.series)


def test_get_series_by_num_exp(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
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
        page = sp.fetch_photometric_series_page(**{f"{op}_num_exposures": split_num})
        assert page.total_matches == 2
        assert len(page.series) == 2
        if op == "min":
            assert all(ps.num_exp >= split_num for ps in page.series)
        if op == "max":
            assert all(ps.num_exp <= split_num for ps in page.series)


def test_get_series_by_mean_and_rms(
    upload_data_token,
    photometric_series_low_flux,
    photometric_series_low_flux_with_outliers,
    photometric_series_high_flux,
):
    sp = client(upload_data_token)
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
        page = sp.fetch_photometric_series_page(**{f"mag_{op.lower()}_than": split_mag})
        assert page.total_matches == 2
        assert len(page.series) == 2
        if op == "Fainter":
            assert all(ps.mean_mag >= split_mag for ps in page.series)
        if op == "Brighter":
            assert all(ps.mean_mag <= split_mag for ps in page.series)

    values = rmses.copy()
    values.sort()
    split_rms = values[1]

    # filter series by rms
    for op in ["min", "max"]:
        page = sp.fetch_photometric_series_page(**{f"{op}_rms": split_rms})
        assert page.total_matches == 2
        assert len(page.series) == 2
        if op == "min":
            assert all(ps.rms_mag >= split_rms for ps in page.series)
        if op == "max":
            assert all(ps.rms_mag <= split_rms for ps in page.series)


def test_get_series_by_robust_mean_mag(
    upload_data_token, photometric_series_low_flux_with_outliers
):
    sp = client(upload_data_token)
    ps = photometric_series_low_flux_with_outliers

    # make sure there is only one series with this name
    page = sp.fetch_photometric_series_page(series_name="test_series_outliers")
    assert page.total_matches == 1
    assert len(page.series) == 1
    assert page.series[0].id == ps.id

    # the mean magnitude is brighter because of outliers
    page = sp.fetch_photometric_series_page(
        series_name="test_series_outliers",
        mag_brighter_than=ps.robust_mag - 0.01,
    )
    assert page.total_matches == 1
    assert len(page.series) == 1
    assert page.series[0].id == ps.id

    # searching for mean magnitude fainter than the mean mag
    page = sp.fetch_photometric_series_page(
        series_name="test_series_outliers",
        mag_brighter_than=ps.mean_mag - 0.01,
    )
    assert page.total_matches == 0
    assert len(page.series) == 0

    # if we choose to measure by robust mean, we also get no results
    page = sp.fetch_photometric_series_page(
        series_name="test_series_outliers",
        mag_brighter_than=ps.robust_mag - 0.01,
        use_robust_mag_and_rms=True,
    )
    assert page.total_matches == 0
    assert len(page.series) == 0


def test_get_series_by_robust_rms(
    upload_data_token, photometric_series_low_flux_with_outliers
):
    sp = client(upload_data_token)
    ps = photometric_series_low_flux_with_outliers

    # make sure there is only one series with this name
    page = sp.fetch_photometric_series_page(series_name="test_series_outliers")
    assert page.total_matches == 1
    assert len(page.series) == 1
    assert page.series[0].id == ps.id

    # the magnitude RMS is bigger because of outliers
    page = sp.fetch_photometric_series_page(
        series_name="test_series_outliers",
        min_rms=0.4,
    )
    assert page.total_matches == 1
    assert len(page.series) == 1
    assert page.series[0].id == ps.id

    # searching for smaller RMS fails
    page = sp.fetch_photometric_series_page(
        series_name="test_series_outliers",
        max_rms=0.4,
    )
    assert page.total_matches == 0
    assert len(page.series) == 0

    # if choose to measure by robust mean, the results are reversed
    page = sp.fetch_photometric_series_page(
        series_name="test_series_outliers",
        min_rms=0.4,
        use_robust_mag_and_rms=True,
    )
    assert page.total_matches == 0
    assert len(page.series) == 0

    # searching for smaller RMS now succeeds
    page = sp.fetch_photometric_series_page(
        series_name="test_series_outliers",
        max_rms=0.5,
        use_robust_mag_and_rms=True,
    )
    assert page.total_matches == 1
    assert len(page.series) == 1
    assert page.series[0].id == ps.id


def test_get_series_by_magref(
    upload_data_token,
    photometric_series,
    photometric_series2,
    photometric_series3,
    photometric_series_low_flux,
):
    sp = client(upload_data_token)
    assert photometric_series.magref == 18.1
    assert photometric_series2.magref == 19.2
    assert photometric_series3.magref == 20.3
    assert photometric_series_low_flux.magref is None

    # should retrieve first three series, not the low-flux one
    page = sp.fetch_photometric_series_page(magref_fainter_than=18.1)

    assert page.total_matches >= 3
    assert len(page.series) >= 3
    ids = [s.id for s in page.series]
    assert photometric_series.id in ids
    assert photometric_series2.id in ids
    assert photometric_series3.id in ids
    assert photometric_series_low_flux.id not in ids

    # the opposite:
    page = sp.fetch_photometric_series_page(magref_brighter_than=18.1)

    assert page.total_matches >= 1
    assert len(page.series) >= 1
    ids = [s.id for s in page.series]
    assert photometric_series.id in ids
    assert photometric_series2.id not in ids
    assert photometric_series3.id not in ids
    assert photometric_series_low_flux.id not in ids

    # should retrieve last two series
    page = sp.fetch_photometric_series_page(magref_fainter_than=19.0)

    assert page.total_matches >= 2
    assert len(page.series) >= 2
    ids = [s.id for s in page.series]
    assert photometric_series.id not in ids
    assert photometric_series2.id in ids
    assert photometric_series3.id in ids
    assert photometric_series_low_flux.id not in ids

    # the opposite:
    page = sp.fetch_photometric_series_page(magref_brighter_than=19.0)

    assert page.total_matches >= 1
    assert len(page.series) >= 1
    ids = [s.id for s in page.series]
    assert photometric_series.id in ids
    assert photometric_series2.id not in ids
    assert photometric_series3.id not in ids
    assert photometric_series_low_flux.id not in ids


def test_by_series_by_not_detected(
    upload_data_token, photometric_series_low_flux, photometric_series_undetected
):
    sp = client(upload_data_token)
    assert not photometric_series_undetected.is_detected

    page = sp.fetch_photometric_series_page(detected=True)

    assert page.total_matches >= 1
    assert len(page.series) >= 1
    assert photometric_series_low_flux.id in [ps.id for ps in page.series]
    assert photometric_series_undetected.id not in [ps.id for ps in page.series]

    page = sp.fetch_photometric_series_page(detected=False)

    assert page.total_matches >= 1
    assert len(page.series) >= 1
    assert photometric_series_undetected.id in [ps.id for ps in page.series]
    assert photometric_series_low_flux.id not in [ps.id for ps in page.series]


def test_get_series_by_hash(upload_data_token, photometric_series):
    sp = client(upload_data_token)
    page = sp.fetch_photometric_series_page(file_hash=photometric_series.hash)
    assert page.total_matches == 1
    assert len(page.series) == 1
    assert page.series[0].id == photometric_series.id


@pytest.mark.flaky(reruns=2)
def test_get_series_by_snr(
    upload_data_token,
    photometric_series_low_flux,
    photometric_series_low_flux_with_outliers,
    photometric_series_high_flux,
):
    sp = client(upload_data_token)
    ps_l = photometric_series_low_flux
    ps_h = photometric_series_high_flux
    ps_o = photometric_series_low_flux_with_outliers

    # low flux lightcurves should have SNR~5
    assert 5 < np.median(ps_l.snr) < 15
    assert 5 < np.median(ps_o.snr) < 15

    # high flux lightcurves should have SNR~100
    assert 50 < np.median(ps_h.snr) < 150

    # Thresholds are derived from the fixtures' realized SNRs instead of
    # hardcoded numbers. The fixtures generate noisy random photometry, so
    # any fixed threshold sits within one sigma of the per-run extremes —
    # past versions of these assertions flaked when ps_h.best_snr happened
    # to land just below 100. By computing thresholds that fall strictly
    # between the actual values, the API filter assertions exercise the
    # backend filtering logic without depending on the random draw.

    # ------------------------------------------------------------------
    # median SNR: ps_l and ps_o are low (~10), ps_h is high (~100).
    # ------------------------------------------------------------------
    low_median = min(ps_l.median_snr, ps_o.median_snr)
    median_below_all = low_median / 2  # below every series' median SNR

    # >= median_below_all: all three series pass
    page = sp.fetch_photometric_series_page(min_median_snr=median_below_all)

    ids = [ps.id for ps in page.series]
    assert page.total_matches >= 3
    assert ps_l.id in ids
    assert ps_h.id in ids
    assert ps_o.id in ids

    # <= median_below_all: none pass
    page = sp.fetch_photometric_series_page(max_median_snr=median_below_all)

    ids = [ps.id for ps in page.series]
    assert ps_l.id not in ids
    assert ps_h.id not in ids
    assert ps_o.id not in ids

    # ------------------------------------------------------------------
    # worst SNR: ps_o has a flux=0 outlier so its worst SNR is 0; ps_l
    # and ps_h's worst points sit well above 0. Threshold goes strictly
    # between ps_o.worst_snr and the smaller of (ps_l, ps_h).
    # ------------------------------------------------------------------
    other_worst = min(ps_l.worst_snr, ps_h.worst_snr)
    worst_threshold = (ps_o.worst_snr + other_worst) / 2
    assert ps_o.worst_snr < worst_threshold < other_worst

    # only ps_o's worst SNR is below threshold
    page = sp.fetch_photometric_series_page(max_worst_snr=worst_threshold)

    ids = [ps.id for ps in page.series]
    assert ps_l.id not in ids
    assert ps_h.id not in ids
    assert ps_o.id in ids

    # inverse: ps_l and ps_h have worst SNR above threshold
    page = sp.fetch_photometric_series_page(min_worst_snr=worst_threshold)

    ids = [ps.id for ps in page.series]
    assert ps_l.id in ids
    assert ps_h.id in ids
    assert ps_o.id not in ids

    # ------------------------------------------------------------------
    # best SNR: ps_h and ps_o (whose 5000/6000 outliers produce huge SNRs)
    # have best SNR far above ps_l's. Threshold goes strictly between
    # ps_l.best_snr and the smaller of (ps_h, ps_o).
    # ------------------------------------------------------------------
    high_best = min(ps_h.best_snr, ps_o.best_snr)
    best_threshold = (ps_l.best_snr + high_best) / 2
    assert ps_l.best_snr < best_threshold < high_best

    page = sp.fetch_photometric_series_page(min_best_snr=best_threshold)

    ids = [ps.id for ps in page.series]
    assert ps_l.id not in ids
    assert ps_h.id in ids
    assert ps_o.id in ids

    page = sp.fetch_photometric_series_page(max_best_snr=best_threshold)

    ids = [ps.id for ps in page.series]
    assert ps_l.id in ids
    assert ps_h.id not in ids
    assert ps_o.id not in ids


def test_get_series_sorting(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
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
        page = sp.fetch_photometric_series_page(sort_by=key)

        assert page.total_matches >= 3
        series_list = page.series
        assert len(series_list) >= 3
        assert set(ids).issubset([ps.id for ps in series_list])
        for i in range(len(ids) - 1):
            assert getattr(series_list[i], key) <= getattr(series_list[i + 1], key)

        page = sp.fetch_photometric_series_page(sort_by=key, sort_order="desc")

        assert page.total_matches >= 3
        series_list = page.series
        assert len(series_list) >= 3
        assert set(ids).issubset([ps.id for ps in series_list])
        for i in range(len(ids) - 1):
            assert getattr(series_list[i], key) >= getattr(series_list[i + 1], key)


def test_get_series_paged(
    upload_data_token, photometric_series, photometric_series2, photometric_series3
):
    sp = client(upload_data_token)
    ids = [photometric_series.id, photometric_series2.id, photometric_series3.id]

    # get all three series
    page = sp.fetch_photometric_series_page()

    assert page.total_matches >= 3
    assert len(page.series) >= 3
    assert set(ids).issubset([ps.id for ps in page.series])

    # get the first two series
    page = sp.fetch_photometric_series_page(num_per_page=2)

    assert page.total_matches >= 3
    assert len(page.series) == 2
    page1_ids = [ps.id for ps in page.series]

    # get the first two series
    page = sp.fetch_photometric_series_page(num_per_page=2, page_number=2)

    assert page.total_matches >= 3
    assert 1 <= len(page.series) <= 2
    page2_ids = [ps.id for ps in page.series]
    assert set(page1_ids).isdisjoint(page2_ids)


def test_download_formats_single_series(upload_data_token, photometric_series):
    sp = client(upload_data_token)
    # regular download of a single series
    # raw api: raw-JSON shape assertion the typed model would mask
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
    # raw api: raw-JSON shape assertion the typed model would mask
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
    ps3 = sp.fetch_photometric_series(photometric_series.id, data_format="hdf5")
    assert photometric_series.obj_id == ps3.obj_id
    assert photometric_series.num_exp == ps3.num_exp

    df, metadata = load_dataframe_from_bytestream(ps3.data)

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
        ps4 = sp.fetch_photometric_series(photometric_series.id, data_format="none")

        assert photometric_series.origin == ps4.origin
        assert photometric_series.num_exp == ps4.num_exp
        assert ps4.data is None

        # download a single series using wrong format='foobar'
        with pytest.raises(SkyPortalError, match='Invalid dataFormat: "foobar"') as err:
            sp.fetch_photometric_series(photometric_series.id, data_format="foobar")
        assert err.value.status_code == 400


def test_download_formats_multiple_series(
    upload_data_token, photometric_series, photometric_series2
):
    sp = client(upload_data_token)
    refs = [photometric_series, photometric_series2]

    # regular download of two series
    # raw api: raw-JSON shape assertion the typed model would mask (the
    # server-default dataFormat is under test; the typed client always sends it)
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
    page = sp.fetch_photometric_series_page(data_format="none")
    assert page.total_matches >= 2
    series = page.series
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
            assert any(getattr(ref_ps, key) == getattr(ps, key) for ps in series)

    # downloading multiple series with format='none' does not return any data
    for ps in series:
        assert ps.data is None

    # download multiple series using format='json'
    page = sp.fetch_photometric_series_page(data_format="json")
    assert page.total_matches >= 2
    series = page.series
    assert len(series) >= 2

    # first match each returned series dict to the reference series
    pairs = []
    for ref_ps in refs:
        for ps in series:
            if ref_ps.id == ps.id:
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
            assert getattr(ref_ps, key) == getattr(ps, key)

        # this time we should get the data as a dict of lists
        assert isinstance(ps.data, dict)
        for key in ["mag", "mjd"]:
            assert key in ps.data
            assert isinstance(ps.data[key], list)
            assert len(ps.data[key]) == ps.num_exp
            assert ps.data[key] == ref_ps.data[key].to_list()

    # download multiple series using the HDF5 format
    page = sp.fetch_photometric_series_page(data_format="hdf5")
    assert page.total_matches >= 2
    series = page.series
    assert len(series) >= 2

    # first match each returned series dict to the reference series
    pairs = []
    for ref_ps in refs:
        for ps in series:
            if ref_ps.id == ps.id:
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
            assert getattr(ref_ps, key) == getattr(ps, key)

        # this time the data should be a bytestream convertible to dataframe
        df, metadata = load_dataframe_from_bytestream(ps.data)

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
    with pytest.raises(SkyPortalError, match='Invalid dataFormat: "foobar"') as err:
        sp.fetch_photometric_series_page(data_format="foobar")
    assert err.value.status_code == 400
