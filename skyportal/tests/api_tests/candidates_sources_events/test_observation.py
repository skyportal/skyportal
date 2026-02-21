import os
import time

import numpy as np
import pandas as pd
import pytest

from skyportal.tests import api
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


def test_observation(super_admin_token, gcn_GW190425):
    dateobs = gcn_GW190425.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    telescope_id, instrument_id, telescope_name, instrument_name = (
        add_telescope_and_instrument("ZTF", super_admin_token, list(range(5)))
    )

    datafile = (
        f"{os.path.dirname(__file__)}/../../../../data/sample_observation_data.csv"
    )
    data = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "observationData": pd.read_csv(datafile).to_dict(orient="list"),
    }

    status, data = api("POST", "observation", data=data, token=super_admin_token)

    assert status == 200
    assert data["status"] == "success"

    # wait for the executed observations to populate
    time.sleep(15)

    data = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "startDate": "2019-04-25 08:18:05",
        "endDate": "2019-04-28 08:18:05",
        "localizationDateobs": dateobs,
        "localizationName": "bayestar.fits.gz",
        "localizationCumprob": 1.01,
        "returnStatistics": True,
        "numPerPage": 1000,
    }

    status, data = api("GET", "observation", params=data, token=super_admin_token)

    assert status == 200
    data = data["data"]
    assert len(data["observations"]) == 10
    assert np.isclose(data["probability"], 2.582514047833091e-05)
    assert any(
        d["obstime"] == "2019-04-25T08:18:18.002909" and d["observation_id"] == 84434604
        for d in data["observations"]
    )

    observation_id = None
    for d in data["observations"]:
        if d["observation_id"] == 84434604:
            observation_id = d["id"]
            break

    data = {
        "startDate": "2019-04-25 08:18:05",
        "endDate": "2019-04-28 08:18:05",
        "localizationDateobs": "2019-04-25T08:18:05",
        "localizationName": "bayestar.fits.gz",
        "localizationCumprob": 1.01,
    }
    status, data = api(
        "GET",
        f"observation/simsurvey/{instrument_id}",
        params=data,
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "DELETE", f"observation/{observation_id}", token=super_admin_token
    )
    assert status == 200

    data = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "startDate": "2019-04-25 08:18:05",
        "endDate": "2019-04-28 08:18:05",
        "localizationDateobs": "2019-04-25T08:18:05",
        "localizationName": "bayestar.fits.gz",
        "localizationCumprob": 1.01,
        "returnStatistics": True,
        "numPerPage": 1000,
    }

    status, data = api("GET", "observation", params=data, token=super_admin_token)
    assert status == 200
    data = data["data"]

    assert len(data["observations"]) == 9
    assert not any(
        d["obstime"] == "2019-04-25T08:18:18.002909" and d["observation_id"] == 84434604
        for d in data["observations"]
    )

    # delete the event
    status, data = api(
        "DELETE", "gcn_event/2019-04-25T08:18:05", token=super_admin_token
    )

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


@pytest.mark.flaky(reruns=2)
def test_observation_radec(super_admin_token):
    telescope_id, instrument_id, telescope_name, instrument_name = (
        add_telescope_and_instrument("ZTF", super_admin_token, list(range(5)))
    )

    datafile = f"{os.path.dirname(__file__)}/../../../../data/sample_observation_data_radec.csv"
    data = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "observationData": pd.read_csv(datafile).to_dict(orient="list"),
    }

    status, data = api("POST", "observation", data=data, token=super_admin_token)

    assert status == 200
    assert data["status"] == "success"

    params = {
        "startDate": "2019-04-25 08:18:05",
        "endDate": "2019-04-28 08:18:05",
    }

    # wait for the executed observations to populate
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            status, data = api(
                "GET", "observation", params=params, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data) == 10
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    assert any(
        d["obstime"] == "2019-04-25T08:18:18.002909" and d["observation_id"] == 94434604
        for d in data["observations"]
    )

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


@pytest.mark.flaky(reruns=2)
def test_observation_isot(super_admin_token):
    telescope_id, instrument_id, telescope_name, instrument_name = (
        add_telescope_and_instrument("ZTF", super_admin_token, list(range(5)))
    )

    datafile = (
        f"{os.path.dirname(__file__)}/../../../../data/sample_observation_data_isot.csv"
    )
    data = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "observationData": pd.read_csv(datafile).to_dict(orient="list"),
    }

    status, data = api("POST", "observation", data=data, token=super_admin_token)

    assert status == 200
    assert data["status"] == "success"

    params = {
        "startDate": "2019-04-25 08:18:05",
        "endDate": "2019-04-28 08:18:05",
    }

    # wait for the executed observations to populate
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            status, data = api(
                "GET", "observation", params=params, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data) == 10
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(2)

    assert any(
        d["obstime"] == "2019-04-25T08:18:18" and d["observation_id"] == 94434604
        for d in data["observations"]
    )

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
