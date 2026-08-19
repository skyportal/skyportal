import contextlib
import os
import time

import numpy as np
import pandas as pd
import pytest
from skyportal_py import SkyPortalError
from skyportal_py.observations import ObservationPost

from skyportal.tests import api, client
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

    sp = client(super_admin_token)
    sp.post_observation(
        ObservationPost(
            telescope_name=telescope_name,
            instrument_name=instrument_name,
            observation_data=pd.read_csv(datafile).to_dict(orient="list"),
        )
    )

    # wait for the executed observations to populate
    time.sleep(15)

    page = sp.fetch_observations(
        telescope_name=telescope_name,
        instrument_name=instrument_name,
        start_date="2019-04-25 08:18:05",
        end_date="2019-04-28 08:18:05",
        localization_dateobs=dateobs,
        localization_name="bayestar.fits.gz",
        localization_cumprob=1.01,
        return_statistics=True,
        num_per_page=1000,
    )

    assert len(page.observations) == 10
    assert np.isclose(page.probability, 2.582514047833091e-05)
    assert any(
        d.obstime.isoformat() == "2019-04-25T08:18:18.002909"
        and d.observation_id == 84434604
        for d in page.observations
    )

    observation_id = None
    for d in page.observations:
        if d.observation_id == 84434604:
            observation_id = d.id
            break

    sp.fetch_observation_simsurvey(
        instrument_id,
        start_date="2019-04-25 08:18:05",
        end_date="2019-04-28 08:18:05",
        localization_dateobs="2019-04-25T08:18:05",
        localization_name="bayestar.fits.gz",
        localization_cumprob=1.01,
    )

    sp.delete_observation(observation_id)

    page = sp.fetch_observations(
        telescope_name=telescope_name,
        instrument_name=instrument_name,
        start_date="2019-04-25 08:18:05",
        end_date="2019-04-28 08:18:05",
        localization_dateobs="2019-04-25T08:18:05",
        localization_name="bayestar.fits.gz",
        localization_cumprob=1.01,
        return_statistics=True,
        num_per_page=1000,
    )

    assert len(page.observations) == 9
    assert not any(
        d.obstime.isoformat() == "2019-04-25T08:18:18.002909"
        and d.observation_id == 84434604
        for d in page.observations
    )

    # delete the event; original test issues this DELETE without checking the response
    with contextlib.suppress(SkyPortalError):
        sp.delete_gcn_event("2019-04-25T08:18:05")

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


@pytest.mark.flaky(reruns=2)
def test_observation_radec(super_admin_token):
    telescope_id, instrument_id, telescope_name, instrument_name = (
        add_telescope_and_instrument("ZTF", super_admin_token, list(range(5)))
    )

    datafile = f"{os.path.dirname(__file__)}/../../../../data/sample_observation_data_radec.csv"

    client(super_admin_token).post_observation(
        ObservationPost(
            telescope_name=telescope_name,
            instrument_name=instrument_name,
            observation_data=pd.read_csv(datafile).to_dict(orient="list"),
        )
    )

    params = {
        "startDate": "2019-04-25 08:18:05",
        "endDate": "2019-04-28 08:18:05",
    }

    # wait for the executed observations to populate
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            # raw api: raw-JSON shape assertion (len of the response dict) the typed model would mask
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

    client(super_admin_token).post_observation(
        ObservationPost(
            telescope_name=telescope_name,
            instrument_name=instrument_name,
            observation_data=pd.read_csv(datafile).to_dict(orient="list"),
        )
    )

    params = {
        "startDate": "2019-04-25 08:18:05",
        "endDate": "2019-04-28 08:18:05",
    }

    # wait for the executed observations to populate
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            # raw api: raw-JSON shape assertion (len of the response dict) the typed model would mask
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
