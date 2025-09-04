import os
import time
import uuid

import numpy as np
from astropy.table import Table

from skyportal.tests import api
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


def test_observation_plan_tiling(super_admin_token, public_group, gcn_GW190814):
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")
    gcnevent_id = gcn_GW190814.id
    localization_id = gcn_GW190814.localizations[0].id

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
        "types": ["observation_plan"],
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    allocation_id = data["data"]["id"]

    requests_data = [
        {
            "allocation_id": allocation_id,
            "gcnevent_id": gcnevent_id,
            "localization_id": localization_id,
            "payload": {
                "start_date": "2020-07-16 01:01:01",
                "end_date": "2020-07-17 01:01:01",
                "filter_strategy": "block",
                "schedule_strategy": "tiling",
                "schedule_type": "greedy_slew",
                "exposure_time": 300,
                "filters": "ztfr",
                "maximum_airmass": 2.0,
                "integrated_probability": 100,
                "minimum_time_difference": 30,
                "queue_name": str(uuid.uuid4()),
                "program_id": "Partnership",
                "subprogram_name": "GRB",
                "galactic_latitude": 10,
            },
        }
        for _ in range(2)
    ]

    for request_data in requests_data:
        status, data = api(
            "POST", "observation_plan", data=request_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    # wait for the observation plans to finish, we added some patience later, but we know that it takes at least 30 seconds
    time.sleep(10)

    n_retries = 0
    while n_retries < 10:
        try:
            status, data = api(
                "GET",
                "observation_plan",
                params={
                    "includePlannedObservations": "true",
                    "dateobs": dateobs,
                    "instrumentID": instrument_id,
                },
                token=super_admin_token,
            )
            assert status == 200
            assert data["status"] == "success"

            # get those which have been created on the right event
            data = [
                d
                for d in data["data"]["requests"]
                if d["gcnevent_id"] == gcnevent_id
                and d["allocation_id"] == allocation_id
            ]
            assert len(data) == len(requests_data)
            for i, d in enumerate(data):
                assert any(
                    d["payload"] == request_data["payload"]
                    for request_data in requests_data
                )
                observation_plans = d["observation_plans"]
                assert len(observation_plans) == 1
                observation_plan = observation_plans[0]

                assert any(
                    observation_plan["plan_name"]
                    == request_data["payload"]["queue_name"]
                    for request_data in requests_data
                )
                assert any(
                    observation_plan["validity_window_start"]
                    == request_data["payload"]["start_date"].replace(" ", "T")
                    for request_data in requests_data
                )
                # same with the validity window start
                assert any(
                    observation_plan["validity_window_start"]
                    == request_data["payload"]["start_date"].replace(" ", "T")
                    for request_data in requests_data
                )
                # same with the validity window end
                assert any(
                    observation_plan["validity_window_end"]
                    == request_data["payload"]["end_date"].replace(" ", "T")
                    for request_data in requests_data
                )

                planned_observations = observation_plan["planned_observations"]

                assert all(
                    obs["filt"] == requests_data[0]["payload"]["filters"]
                    for obs in planned_observations
                )
                assert all(
                    obs["exposure_time"]
                    == int(requests_data[0]["payload"]["exposure_time"])
                    for obs in planned_observations
                )
            break
        except AssertionError:
            n_retries += 1
            time.sleep(5)

    assert n_retries < 10

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


def test_observation_plan_galaxy(
    super_admin_token, view_only_token, public_group, gcn_GW190814
):
    gcnevent_id = gcn_GW190814.id
    localization_id = gcn_GW190814.localizations[0].id

    catalog_name = "test_galaxy_catalog"
    # in case the catalog already exists, delete it.
    status, data = api(
        "DELETE", f"galaxy_catalog/{catalog_name}", token=super_admin_token
    )

    datafile = f"{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5"
    data = {
        "catalog_name": catalog_name,
        "catalog_data": Table.read(datafile)
        .to_pandas()
        .replace({np.nan: None})
        .to_dict(orient="list"),
    }

    status, data = api("POST", "galaxy_catalog", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(200, 250))
    )

    nretries = 0
    galaxies_loaded = False
    while nretries < 10:
        status, data = api(
            "GET",
            "galaxy_catalog",
            token=view_only_token,
            params={"catalog_name": catalog_name},
        )
        assert status == 200
        data = data["data"]["galaxies"]
        if len(data) == 92 and any(
            d["name"] == "6dFgs gJ0001313-055904" and d["mstar"] == 336.60756522868667
            for d in data
        ):
            galaxies_loaded = True
            break
        nretries = nretries + 1
        time.sleep(5)

    assert nretries < 10
    assert galaxies_loaded

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
        "types": ["observation_plan"],
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    allocation_id = data["data"]["id"]

    requests_data = [
        {
            "allocation_id": allocation_id,
            "gcnevent_id": gcnevent_id,
            "localization_id": localization_id,
            "payload": {
                "start_date": "2020-07-16 01:01:01",
                "end_date": "2020-07-17 01:01:01",
                "filter_strategy": "block",
                "schedule_strategy": "galaxy",
                "galaxy_catalog": catalog_name,
                "schedule_type": "greedy_slew",
                "exposure_time": 300,
                "filters": "ztfr",
                "maximum_airmass": 2.5,
                "integrated_probability": 100,
                "minimum_time_difference": 30,
                "queue_name": str(uuid.uuid4()),
                "program_id": "Partnership",
                "subprogram_name": "GRB",
                "galactic_latitude": 10,
            },
        }
        for _ in range(2)
    ]

    for request_data in requests_data:
        status, data = api(
            "POST", "observation_plan", data=request_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    # wait for the observation plans to finish, we added some patience later, but we know that it takes at least 30 seconds
    time.sleep(10)

    n_retries = 0
    while n_retries < 10:
        try:
            status, data = api(
                "GET",
                "observation_plan",
                params={"includePlannedObservations": "true"},
                token=super_admin_token,
            )
            assert status == 200
            assert data["status"] == "success"

            # get those which have been created on the right event
            data = [
                d
                for d in data["data"]["requests"]
                if d["gcnevent_id"] == gcnevent_id
                and d["allocation_id"] == allocation_id
            ]
            assert len(data) == len(requests_data)

            for i, d in enumerate(data):
                assert any(
                    d["payload"]["queue_name"] == request_data["payload"]["queue_name"]
                    for request_data in requests_data
                )
                observation_plans = d["observation_plans"]
                assert len(observation_plans) == 1
                observation_plan = observation_plans[0]

                assert any(
                    observation_plan["plan_name"]
                    == request_data["payload"]["queue_name"]
                    for request_data in requests_data
                )
                assert observation_plan["validity_window_start"] == requests_data[0][
                    "payload"
                ]["start_date"].replace(" ", "T")
                assert observation_plan["validity_window_end"] == requests_data[0][
                    "payload"
                ]["end_date"].replace(" ", "T")

                planned_observations = observation_plan["planned_observations"]
                assert len(planned_observations) >= 2

                assert all(
                    obs["filt"] == requests_data[i]["payload"]["filters"]
                    for obs in planned_observations
                )
                assert all(
                    obs["exposure_time"]
                    == int(requests_data[i]["payload"]["exposure_time"])
                    for obs in planned_observations
                )
            break
        except AssertionError:
            n_retries = n_retries + 1
            time.sleep(5)

    assert n_retries < 10

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
