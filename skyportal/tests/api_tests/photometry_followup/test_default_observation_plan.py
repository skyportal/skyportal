import os
import time
import uuid

import numpy as np
import pytest
from skyportal_py import SkyPortalError
from skyportal_py.allocations import AllocationPost
from skyportal_py.gcn_events import GcnEventPost
from skyportal_py.observation_plans import DefaultObservationPlanPost

from skyportal.tests import client
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


@pytest.mark.flaky(reruns=2)
def test_default_observation_plan_tiling(super_admin_token, public_group):
    sp = client(super_admin_token)
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
        )
    ).id

    default_plan_name = str(uuid.uuid4())

    request_data = DefaultObservationPlanPost(
        allocation_id=allocation_id,
        default_plan_name=default_plan_name,
        payload={
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
    )

    id = sp.post_default_observation_plan(request_data).id

    assert sp.fetch_default_observation_plan(id).allocation_id == allocation_id

    # we create a second plan, to see if generating both at the same time works
    default_plan_name_2 = str(uuid.uuid4())
    request_data.default_plan_name = default_plan_name_2
    id = sp.post_default_observation_plan(request_data).id

    assert sp.fetch_default_observation_plan(id).allocation_id == allocation_id

    datafile = f"{os.path.dirname(__file__)}/../../../../data/GW190814.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = GcnEventPost(xml=payload)

    dateobs = "2019-08-14T21:10:39"
    try:
        sp.fetch_gcn_event(dateobs)
    except SkyPortalError:
        gcnevent_id = sp.post_gcn_event(event_data).gcnevent_id
    else:
        # we delete the event and re-add it
        sp.delete_gcn_event(dateobs)
        gcnevent_id = sp.post_gcn_event(event_data).gcnevent_id

    # wait for event to load
    for n_times in range(26):
        try:
            sp.fetch_gcn_event(dateobs)
            break
        except SkyPortalError:
            time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    for n_times_2 in range(26):
        try:
            localization = sp.fetch_localization(
                "2019-08-14T21:10:39", "LALInference.v1.fits.gz", include_2d_map=True
            )
        except SkyPortalError:
            time.sleep(2)
        else:
            assert localization.dateobs.isoformat() == dateobs
            assert localization.localization_name == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(localization.flat_2d), 1)
            break
    assert n_times_2 < 25

    # wait for the plans to be processed
    time.sleep(10)

    n_retries = 0
    while n_retries < 10:
        try:
            # now we want to see if any observation plans were created
            requests = sp.fetch_gcn_event_observation_plan_requests(gcnevent_id)
            assert len(requests) > 0
            generated_by_default = [d.allocation_id == allocation_id for d in requests]
            assert sum(generated_by_default) == 2
            break
        except (AssertionError, SkyPortalError):
            n_retries += 1
            time.sleep(5)

    assert n_retries < 10

    sp.delete_default_observation_plan(id)

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
