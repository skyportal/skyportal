import os
import uuid

import numpy as np
from astropy.time import Time

from skyportal.tests import api


def test_token_user_post_get_mmadetector(super_admin_token):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "nickname": name,
        "type": "gravitational-wave",
        "fixed_location": True,
        "lat": 0.0,
        "lon": 0.0,
    }

    status, data = api("POST", "mmadetector", data=post_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    mmadetector_id = data["data"]["id"]
    status, data = api("GET", f"mmadetector/{mmadetector_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    for key in post_data:
        assert data["data"][key] == post_data[key]


def test_fetch_mmadetector_by_name(super_admin_token):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "nickname": name,
        "type": "gravitational-wave",
        "fixed_location": True,
        "lat": 0.0,
        "lon": 0.0,
    }

    status, data = api("POST", "mmadetector", data=post_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"mmadetector?name={name}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    for key in post_data:
        assert data["data"][0][key] == post_data[key]


def test_token_user_update_mmadetector(super_admin_token):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "mmadetector",
        data={
            "name": name,
            "nickname": name,
            "type": "gravitational-wave",
            "fixed_location": True,
            "lat": 0.0,
            "lon": 0.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    mmadetector_id = data["data"]["id"]
    status, data = api("GET", f"mmadetector/{mmadetector_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["lon"] == 0.0

    status, data = api(
        "PATCH",
        f"mmadetector/{mmadetector_id}",
        data={
            "name": name,
            "nickname": name,
            "type": "neutrino",
            "fixed_location": True,
            "lat": 0.0,
            "lon": 20.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"mmadetector/{mmadetector_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["lon"] == 20.0
    assert data["data"]["type"] == "neutrino"


def test_token_user_delete_mmadetector(super_admin_token):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "mmadetector",
        data={
            "name": name,
            "nickname": name,
            "type": "gravitational-wave",
            "fixed_location": True,
            "lat": 0.0,
            "lon": 0.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    mmadetector_id = data["data"]["id"]
    status, data = api("GET", f"mmadetector/{mmadetector_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "DELETE", f"mmadetector/{mmadetector_id}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"mmadetector/{mmadetector_id}", token=super_admin_token)
    assert status == 400


def test_mmadetector_spectrum(super_admin_token):
    datafile = f"{os.path.dirname(__file__)}/../data/aligo_O4high_noise_spectrum.txt"
    data_out = np.loadtxt(datafile)
    frequencies = data_out[:, 0]
    amplitudes = data_out[:, 1]

    start_time = Time("2023-03-01T00:00:00", format="isot")
    end_time = Time("2024-06-01T00:00:00", format="isot")

    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "mmadetector",
        data={
            "name": name,
            "nickname": name,
            "type": "gravitational-wave",
            "fixed_location": True,
            "lat": 0.0,
            "lon": 0.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    detector_id = data["data"]["id"]

    data = {
        "frequencies": frequencies.tolist(),
        "amplitudes": amplitudes.tolist(),
        "start_time": start_time.isot,
        "end_time": end_time.isot,
        "detector_id": detector_id,
    }

    status, data = api(
        "POST",
        "mmadetector/spectra",
        data=data,
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id = data["data"]["id"]

    status, data = api(
        "GET", f"mmadetector/spectra/{spectrum_id}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    assert np.array_equal(frequencies, data["data"]["frequencies"])
    assert np.array_equal(amplitudes, data["data"]["amplitudes"])
    assert start_time == Time(data["data"]["start_time"], format="isot")
    assert end_time == Time(data["data"]["end_time"], format="isot")

    status, data = api("GET", "mmadetector/spectra", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    data = data["data"][0]

    assert np.array_equal(frequencies, data["frequencies"])
    assert np.array_equal(amplitudes, data["amplitudes"])
    assert start_time == Time(data["start_time"], format="isot")
    assert end_time == Time(data["end_time"], format="isot")

    status, data = api(
        "DELETE", f"mmadetector/spectra/{spectrum_id}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"mmadetector/spectra/{spectrum_id}", token=super_admin_token
    )
    assert status == 403


def test_mmadetector_time_intervals(super_admin_token):
    datafile = f"{os.path.dirname(__file__)}/../data/H1L1_O3_time_intervals.txt"
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
    status, data = api(
        "POST",
        "mmadetector",
        data={
            "name": name,
            "nickname": name,
            "type": "gravitational-wave",
            "fixed_location": True,
            "lat": 0.0,
            "lon": 0.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    detector_id = data["data"]["id"]

    data = {
        "time_intervals": time_intervals,
        "detector_id": detector_id,
    }

    status, data = api(
        "POST",
        "mmadetector/time_intervals",
        data=data,
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    time_interval_ids = data["data"]["ids"]

    time_interval_id = time_interval_ids[0]
    status, data = api(
        "GET", f"mmadetector/time_intervals/{time_interval_id}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["time_interval"] == test_time_interval

    params = {"detectorIDs": [detector_id]}
    status, data = api(
        "GET", "mmadetector/time_intervals", params=params, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert any(seg["time_interval"] == test_time_interval for seg in data["data"])
    assert all(seg["id"] in time_interval_ids for seg in data["data"])

    data = {
        "time_interval": time_intervals[1],
        "detector_id": detector_id,
    }

    status, data = api(
        "PATCH",
        f"mmadetector/time_intervals/{time_interval_id}",
        data=data,
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    time_interval_id = time_interval_ids[0]
    status, data = api(
        "GET", f"mmadetector/time_intervals/{time_interval_id}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["time_interval"] == test_time_interval_2

    for time_interval_id in time_interval_ids:
        status, data = api(
            "DELETE",
            f"mmadetector/time_intervals/{time_interval_id}",
            token=super_admin_token,
        )
        assert status == 200
        assert data["status"] == "success"

        status, data = api(
            "GET",
            f"mmadetector/time_intervals/{time_interval_id}",
            token=super_admin_token,
        )
        assert status == 403
