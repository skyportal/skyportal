import os
import time
import uuid

import numpy as np
import pytest

from skyportal.tests import api
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


@pytest.mark.flaky(reruns=2)
def test_default_observation_plan_tiling(super_admin_token, public_group):
    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(200, 250))
    )

    request_data = {
        "group_id": public_group.id,
        "instrument_id": instrument_id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    allocation_id = data["data"]["id"]

    default_plan_name = str(uuid.uuid4())

    request_data = {
        "allocation_id": allocation_id,
        "default_plan_name": default_plan_name,
        "payload": {
            "filter_strategy": "block",
            "schedule_strategy": "tiling",
            "schedule_type": "greedy_slew",
            "exposure_time": 300,
            "filters": "ztfr",
            "maximum_airmass": 2.0,
            "integrated_probability": 100,
            "minimum_time_difference": 30,
            "program_id": "Partnership",
            "subprogram_name": "GRB",
        },
    }

    status, data = api(
        "POST", "default_observation_plan", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    status, data = api(
        "GET",
        f"default_observation_plan/{id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["allocation_id"] == allocation_id

    # we create a second plan, to see if generating both at the same time works
    default_plan_name_2 = str(uuid.uuid4())
    request_data["default_plan_name"] = default_plan_name_2
    status, data = api(
        "POST", "default_observation_plan", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    id = data["data"]["id"]

    status, data = api(
        "GET",
        f"default_observation_plan/{id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["allocation_id"] == allocation_id

    datafile = f"{os.path.dirname(__file__)}/../../../../data/GW190814.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2019-08-14T21:10:39"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)

    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"
    else:
        # we delete the event and re-add it
        status, data = api("DELETE", f"gcn_event/{dateobs}", token=super_admin_token)
        assert status == 200
        assert data["status"] == "success"

        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    gcnevent_id = data["data"]["gcnevent_id"]

    # wait for event to load
    for n_times in range(26):
        status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
        if data["status"] == "success":
            break
        time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}
    for n_times_2 in range(26):
        status, data = api(
            "GET",
            "localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz",
            token=super_admin_token,
            params=params,
        )

        if data["status"] == "success":
            data = data["data"]
            assert data["dateobs"] == dateobs
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25

    # wait for the plans to be processed
    time.sleep(10)

    n_retries = 0
    while n_retries < 10:
        try:
            # now we want to see if any observation plans were created
            status, data = api(
                "GET",
                f"gcn_event/{gcnevent_id}/observation_plan_requests",
                token=super_admin_token,
            )
            assert status == 200
            assert data["status"] == "success"
            assert len(data["data"]) > 0
            generated_by_default = [
                d["allocation_id"] == allocation_id for d in data["data"]
            ]
            assert sum(generated_by_default) == 2
            break
        except AssertionError:
            n_retries += 1
            time.sleep(5)

    assert n_retries < 10

    status, data = api(
        "DELETE",
        f"default_observation_plan/{id}",
        token=super_admin_token,
    )
    assert status == 200

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
