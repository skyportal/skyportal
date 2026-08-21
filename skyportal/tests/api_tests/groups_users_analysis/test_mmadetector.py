import os
import uuid

import numpy as np
import pytest
from astropy.time import Time
from skyportal_py import SkyPortalError
from skyportal_py.mmadetectors import MMADetectorPost, MMADetectorSpectrumPost

from skyportal.tests import client


def test_token_user_post_get_mmadetector(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    post_data = MMADetectorPost(
        name=name,
        nickname=name,
        type="gravitational-wave",
        fixed_location=True,
        lat=0.0,
        lon=0.0,
    )

    mmadetector_id = sp.post_mmadetector(post_data).id

    fetched = sp.fetch_mmadetector(mmadetector_id)
    for key, value in post_data.model_dump(exclude_none=True).items():
        assert getattr(fetched, key) == value


def test_fetch_mmadetector_by_name(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    post_data = MMADetectorPost(
        name=name,
        nickname=name,
        type="gravitational-wave",
        fixed_location=True,
        lat=0.0,
        lon=0.0,
    )

    sp.post_mmadetector(post_data)

    matches = sp.fetch_mmadetectors(name=name)
    assert len(matches) == 1
    for key, value in post_data.model_dump(exclude_none=True).items():
        assert getattr(matches[0], key) == value


def test_token_user_update_mmadetector(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    mmadetector_id = sp.post_mmadetector(
        MMADetectorPost(
            name=name,
            nickname=name,
            type="gravitational-wave",
            fixed_location=True,
            lat=0.0,
            lon=0.0,
        )
    ).id

    assert sp.fetch_mmadetector(mmadetector_id).lon == 0.0

    sp.update_mmadetector(
        mmadetector_id,
        name=name,
        nickname=name,
        type="neutrino",
        fixed_location=True,
        lat=0.0,
        lon=20.0,
    )

    fetched = sp.fetch_mmadetector(mmadetector_id)
    assert fetched.lon == 20.0
    assert fetched.type == "neutrino"


def test_token_user_delete_mmadetector(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    mmadetector_id = sp.post_mmadetector(
        MMADetectorPost(
            name=name,
            nickname=name,
            type="gravitational-wave",
            fixed_location=True,
            lat=0.0,
            lon=0.0,
        )
    ).id

    sp.fetch_mmadetector(mmadetector_id)

    sp.delete_mmadetector(mmadetector_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_mmadetector(mmadetector_id)
    assert err.value.status_code == 400


def test_mmadetector_spectrum(super_admin_token):
    sp = client(super_admin_token)
    datafile = f"{os.path.dirname(__file__)}/../../data/aligo_O4high_noise_spectrum.txt"
    data_out = np.loadtxt(datafile)
    frequencies = data_out[:, 0]
    amplitudes = data_out[:, 1]

    start_time = Time("2023-03-01T00:00:00", format="isot")
    end_time = Time("2024-06-01T00:00:00", format="isot")

    name = str(uuid.uuid4())
    detector_id = sp.post_mmadetector(
        MMADetectorPost(
            name=name,
            nickname=name,
            type="gravitational-wave",
            fixed_location=True,
            lat=0.0,
            lon=0.0,
        )
    ).id

    spectrum_id = sp.post_mmadetector_spectrum(
        MMADetectorSpectrumPost(
            frequencies=frequencies.tolist(),
            amplitudes=amplitudes.tolist(),
            start_time=start_time.isot,
            end_time=end_time.isot,
            detector_id=detector_id,
        )
    ).id

    spectrum = sp.fetch_mmadetector_spectrum(spectrum_id)

    assert np.array_equal(frequencies, spectrum.frequencies)
    assert np.array_equal(amplitudes, spectrum.amplitudes)
    assert start_time == Time(spectrum.start_time)
    assert end_time == Time(spectrum.end_time)

    spectrum = sp.fetch_mmadetector_spectra()[0]

    assert np.array_equal(frequencies, spectrum.frequencies)
    assert np.array_equal(amplitudes, spectrum.amplitudes)
    assert start_time == Time(spectrum.start_time)
    assert end_time == Time(spectrum.end_time)

    sp.delete_mmadetector_spectrum(spectrum_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_mmadetector_spectrum(spectrum_id)
    assert err.value.status_code == 403


def test_mmadetector_time_intervals(super_admin_token):
    sp = client(super_admin_token)
    datafile = f"{os.path.dirname(__file__)}/../../data/H1L1_O3_time_intervals.txt"
    data_out = np.loadtxt(datafile)
    time_intervals = []
    for row in data_out:
        start_time = Time(row[1], format="gps")
        end_time = Time(row[2], format="gps")
        time_intervals.append([start_time.isot, end_time.isot])

    test_time_interval = time_intervals[0]
    test_time_interval = [seg.replace(".000", "") for seg in test_time_interval]
    test_time_interval_2 = time_intervals[1]
    test_time_interval_2 = [seg.replace(".000", "") for seg in test_time_interval_2]

    name = str(uuid.uuid4())
    detector_id = sp.post_mmadetector(
        MMADetectorPost(
            name=name,
            nickname=name,
            type="gravitational-wave",
            fixed_location=True,
            lat=0.0,
            lon=0.0,
        )
    ).id

    time_interval_ids = sp.post_mmadetector_time_intervals(
        detector_id, time_intervals
    ).ids

    time_interval_id = time_interval_ids[0]
    interval = sp.fetch_mmadetector_time_interval(time_interval_id)
    assert [t.isoformat() for t in interval.time_interval] == test_time_interval

    intervals = sp.fetch_mmadetector_time_intervals(detector_ids=[detector_id])
    assert any(
        [t.isoformat() for t in seg.time_interval] == test_time_interval
        for seg in intervals
    )
    assert all(seg.id in time_interval_ids for seg in intervals)

    sp.update_mmadetector_time_interval(
        time_interval_id, time_interval=time_intervals[1]
    )

    time_interval_id = time_interval_ids[0]
    interval = sp.fetch_mmadetector_time_interval(time_interval_id)
    assert [t.isoformat() for t in interval.time_interval] == test_time_interval_2

    for time_interval_id in time_interval_ids:
        sp.delete_mmadetector_time_interval(time_interval_id)

        with pytest.raises(SkyPortalError) as err:
            sp.fetch_mmadetector_time_interval(time_interval_id)
        assert err.value.status_code == 403
