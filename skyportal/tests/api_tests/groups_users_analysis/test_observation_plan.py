import os
import uuid

import numpy as np
from astropy.table import Table
from skyportal_py import SkyPortalError
from skyportal_py.allocations import AllocationPost
from skyportal_py.galaxies import GalaxyCatalogPost
from skyportal_py.observation_plans import ObservationPlanPost

from skyportal.tests import client, retry_until
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


def test_observation_plan_tiling(super_admin_token, public_group, gcn_GW190814):
    sp = client(super_admin_token)
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")
    gcnevent_id = gcn_GW190814.id
    localization_id = gcn_GW190814.localizations[0].id

    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(200, 250))
    )

    allocation_id = sp.post_allocation(
        AllocationPost(
            group_id=public_group.id,
            instrument_id=instrument_id,
            pi="Shri Kulkarni",
            hours_allocated=200,
            validity_ranges=[
                {
                    "start_date": "2021-02-27T00:00:00.000Z",
                    "end_date": "3021-07-20T00:00:00.000Z",
                }
            ],
            proposal_id="COO-2020A-P01",
            types=["observation_plan"],
        )
    ).id

    requests_data = [
        ObservationPlanPost(
            allocation_id=allocation_id,
            gcnevent_id=gcnevent_id,
            localization_id=localization_id,
            payload={
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
        )
        for _ in range(2)
    ]

    for request_data in requests_data:
        sp.post_observation_plan(request_data)

    def plans_ready():
        page = sp.fetch_observation_plans(
            include_planned_observations=True,
            dateobs=dateobs,
            instrument_id=instrument_id,
        )

        # get those which have been created on the right event
        requests = [
            d
            for d in page.requests
            if d.gcnevent_id == gcnevent_id and d.allocation_id == allocation_id
        ]
        assert len(requests) == len(requests_data)
        for d in requests:
            assert any(
                d.payload == request_data.payload for request_data in requests_data
            )
            observation_plans = d.observation_plans
            assert len(observation_plans) == 1
            observation_plan = observation_plans[0]

            assert any(
                observation_plan.plan_name == request_data.payload["queue_name"]
                for request_data in requests_data
            )
            assert any(
                observation_plan.validity_window_start.isoformat()
                == request_data.payload["start_date"].replace(" ", "T")
                for request_data in requests_data
            )
            assert any(
                observation_plan.validity_window_end.isoformat()
                == request_data.payload["end_date"].replace(" ", "T")
                for request_data in requests_data
            )

            planned_observations = observation_plan.planned_observations

            assert all(
                obs.filt == requests_data[0].payload["filters"]
                for obs in planned_observations
            )
            assert all(
                obs.exposure_time == int(requests_data[0].payload["exposure_time"])
                for obs in planned_observations
            )
        return [d.id for d in requests]

    request_ids = retry_until(plans_ready, timeout=60)

    # exercise the (async) delete path: DELETE each request and verify it is gone
    for request_id in request_ids:
        sp.delete_observation_plan(request_id)

    page = sp.fetch_observation_plans(dateobs=dateobs, instrument_id=instrument_id)
    remaining = [
        d
        for d in page.requests
        if d.gcnevent_id == gcnevent_id and d.allocation_id == allocation_id
    ]
    assert len(remaining) == 0

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


def test_observation_plan_combined(super_admin_token, public_group, gcn_GW190814):
    """Exercise the combined (submit_multiple) plan-generation path and delete."""
    sp = client(super_admin_token)
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")
    gcnevent_id = gcn_GW190814.id
    localization_id = gcn_GW190814.localizations[0].id

    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(200, 250))
    )

    allocation_id = sp.post_allocation(
        AllocationPost(
            group_id=public_group.id,
            instrument_id=instrument_id,
            pi="Shri Kulkarni",
            hours_allocated=200,
            validity_ranges=[
                {
                    "start_date": "2021-02-27T00:00:00.000Z",
                    "end_date": "3021-07-20T00:00:00.000Z",
                }
            ],
            proposal_id="COO-2020A-P01",
            types=["observation_plan"],
        )
    ).id

    observation_plans = [
        ObservationPlanPost(
            allocation_id=allocation_id,
            gcnevent_id=gcnevent_id,
            localization_id=localization_id,
            payload={
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
        )
        for _ in range(2)
    ]

    # combine_plans=True groups the requests so the queue calls submit_multiple
    sp.post_observation_plans(observation_plans, combine_plans=True)

    def combined_plans_ready():
        page = sp.fetch_observation_plans(
            include_planned_observations=True,
            dateobs=dateobs,
            instrument_id=instrument_id,
        )

        requests = [
            d
            for d in page.requests
            if d.gcnevent_id == gcnevent_id and d.allocation_id == allocation_id
        ]
        assert len(requests) == len(observation_plans)
        # every request should be combined (share a combined_id) and complete
        assert all(d.combined_id is not None for d in requests)
        assert all(d.status == "complete" for d in requests)
        for d in requests:
            assert len(d.observation_plans) == 1
        return [d.id for d in requests]

    request_ids = retry_until(combined_plans_ready, timeout=60)

    # exercise the (async) delete path on the combined requests
    for request_id in request_ids:
        sp.delete_observation_plan(request_id)

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


def test_observation_plan_galaxy(
    super_admin_token, view_only_token, public_group, gcn_GW190814
):
    sp = client(super_admin_token)
    gcnevent_id = gcn_GW190814.id
    localization_id = gcn_GW190814.localizations[0].id

    catalog_name = "test_galaxy_catalog"
    # in case the catalog already exists, delete it.
    try:
        sp.delete_galaxy_catalog(catalog_name)
    except SkyPortalError:
        pass

    datafile = f"{os.path.dirname(__file__)}/../../../../data/CLU_mini.hdf5"
    sp.post_galaxy_catalog(
        GalaxyCatalogPost(
            catalog_name=catalog_name,
            catalog_data=Table.read(datafile)
            .to_pandas()
            .replace({np.nan: None})
            .to_dict(orient="list"),
        )
    )

    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(200, 250))
    )

    def galaxies_loaded():
        galaxies = (
            client(view_only_token).fetch_galaxies(catalog_name=catalog_name).galaxies
        )
        assert len(galaxies) == 92
        assert any(
            d.name == "6dFgs gJ0001313-055904" and d.mstar == 336.60756522868667
            for d in galaxies
        )

    retry_until(galaxies_loaded, timeout=50)

    allocation_id = sp.post_allocation(
        AllocationPost(
            group_id=public_group.id,
            instrument_id=instrument_id,
            pi="Shri Kulkarni",
            hours_allocated=200,
            validity_ranges=[
                {
                    "start_date": "2021-02-27T00:00:00.000Z",
                    "end_date": "3021-07-20T00:00:00.000Z",
                }
            ],
            proposal_id="COO-2020A-P01",
            types=["observation_plan"],
        )
    ).id

    requests_data = [
        ObservationPlanPost(
            allocation_id=allocation_id,
            gcnevent_id=gcnevent_id,
            localization_id=localization_id,
            payload={
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
        )
        for _ in range(2)
    ]

    for request_data in requests_data:
        sp.post_observation_plan(request_data)

    def galaxy_plans_ready():
        page = sp.fetch_observation_plans(include_planned_observations=True)

        # get those which have been created on the right event
        requests = [
            d
            for d in page.requests
            if d.gcnevent_id == gcnevent_id and d.allocation_id == allocation_id
        ]
        assert len(requests) == len(requests_data)

        for i, d in enumerate(requests):
            assert any(
                d.payload["queue_name"] == request_data.payload["queue_name"]
                for request_data in requests_data
            )
            observation_plans = d.observation_plans
            assert len(observation_plans) == 1
            observation_plan = observation_plans[0]

            assert any(
                observation_plan.plan_name == request_data.payload["queue_name"]
                for request_data in requests_data
            )
            assert observation_plan.validity_window_start.isoformat() == requests_data[
                0
            ].payload["start_date"].replace(" ", "T")
            assert observation_plan.validity_window_end.isoformat() == requests_data[
                0
            ].payload["end_date"].replace(" ", "T")

            planned_observations = observation_plan.planned_observations
            assert len(planned_observations) >= 2

            assert all(
                obs.filt == requests_data[i].payload["filters"]
                for obs in planned_observations
            )
            assert all(
                obs.exposure_time == int(requests_data[i].payload["exposure_time"])
                for obs in planned_observations
            )

    retry_until(galaxy_plans_ready, timeout=60)

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
