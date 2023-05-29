import os
import time
import uuid

import numpy as np
import pandas as pd
import pytest
from regions import Regions

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_default_observation_plan_tiling(user, super_admin_token, public_group):

    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': name,
            'nickname': name,
            'lat': 0.0,
            'lon': 0.0,
            'elevation': 0.0,
            'diameter': 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    fielddatafile = f'{os.path.dirname(__file__)}/../../../../data/ZTF_Fields.csv'
    regionsdatafile = f'{os.path.dirname(__file__)}/../../../../data/ZTF_Region.reg'

    instrument_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name,
            'type': 'imager',
            'band': 'Optical',
            'filters': ['ztfr'],
            'telescope_id': telescope_id,
            'api_classname': 'ZTFAPI',
            'api_classname_obsplan': 'ZTFMMAAPI',
            'field_data': pd.read_csv(fielddatafile)[:5].to_dict(orient='list'),
            'field_region': Regions.read(regionsdatafile).serialize(format='ds9'),
            'sensitivity_data': {
                'ztfr': {
                    'limiting_magnitude': 20.3,
                    'magsys': 'ab',
                    'exposure_time': 30,
                    'zeropoint': 26.3,
                }
            },
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    request_data = {
        'group_id': public_group.id,
        'instrument_id': instrument_id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    allocation_id = data['data']['id']

    default_plan_name = str(uuid.uuid4())

    request_data = {
        'allocation_id': allocation_id,
        'default_plan_name': default_plan_name,
        'payload': {
            'filter_strategy': 'block',
            'schedule_strategy': 'tiling',
            'schedule_type': 'greedy_slew',
            'exposure_time': 300,
            'filters': 'ztfr',
            'maximum_airmass': 2.0,
            'integrated_probability': 100,
            'minimum_time_difference': 30,
            'program_id': 'Partnership',
            'subprogram_name': 'GRB',
        },
    }

    status, data = api(
        'POST', 'default_observation_plan', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api(
        'GET',
        f'default_observation_plan/{id}',
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data["data"]["allocation_id"] == allocation_id

    # we create a second plan, to see if generating both at the same time works
    default_plan_name_2 = str(uuid.uuid4())
    request_data["default_plan_name"] = default_plan_name_2
    status, data = api(
        'POST', 'default_observation_plan', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    id = data['data']['id']

    status, data = api(
        'GET',
        f'default_observation_plan/{id}',
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data["data"]["allocation_id"] == allocation_id

    datafile = f'{os.path.dirname(__file__)}/../../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    event_data = {'xml': payload}

    dateobs = "2019-08-14T21:10:39"
    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)

    if status == 404:
        status, data = api(
            'POST', 'gcn_event', data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data['status'] == 'success'

        gcnevent_id = data['data']['gcnevent_id']
    else:
        # we delete the event and re-add it
        gcnevent_id = data['data']['id']
        status, data = api('DELETE', f'gcn_event/{dateobs}', token=super_admin_token)
        assert status == 200
        assert data['status'] == 'success'

        status, data = api(
            'POST', 'gcn_event', data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data['status'] == 'success'

        gcnevent_id = data['data']['gcnevent_id']

    # wait for event to load
    for n_times in range(26):
        status, data = api('GET', f"gcn_event/{dateobs}", token=super_admin_token)
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}
    for n_times_2 in range(26):
        status, data = api(
            'GET',
            'localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            data = data["data"]
            assert data["dateobs"] == dateobs
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25

    # wait for the plans to be processed
    time.sleep(30)

    n_retries = 0
    while n_retries < 15:
        try:
            # now we want to see if any observation plans were created
            status, data = api(
                'GET',
                f"gcn_event/{gcnevent_id}/observation_plan_requests",
                token=super_admin_token,
            )
            assert status == 200
            assert data['status'] == 'success'
            assert len(data['data']) > 0
            generated_by_default = [
                d['allocation_id'] == allocation_id for d in data['data']
            ]
            assert sum(generated_by_default) == 2
            break
        except AssertionError:
            n_retries += 1
            time.sleep(3)

    assert n_retries < 15

    status, data = api(
        'DELETE',
        f'default_observation_plan/{id}',
        token=super_admin_token,
    )
    assert status == 200
