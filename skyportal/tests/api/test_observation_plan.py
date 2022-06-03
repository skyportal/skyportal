import os
import uuid
import pandas as pd
import time
from regions import Regions
from astropy.table import Table
import pytest

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_observation_plan_tiling(
    user, super_admin_token, upload_data_token, view_only_token, public_group
):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    gcnevent_id = data['data']['gcnevent_id']

    dateobs = "2019-04-25 08:18:05"
    skymap = "bayestar.fits.gz"
    status, data = api(
        'GET',
        f'localization/{dateobs}/name/{skymap}',
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    localization_id = data['data']['id']

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

    fielddatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv'
    regionsdatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Region.reg'

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
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    # wait for the fields to populate
    time.sleep(15)

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

    request_data = {
        'allocation_id': allocation_id,
        'gcnevent_id': gcnevent_id,
        'localization_id': localization_id,
        'payload': {
            'start_date': '2019-04-25 01:01:01',
            'end_date': '2019-04-27 01:01:01',
            'filter_strategy': 'block',
            'schedule_strategy': 'tiling',
            'schedule_type': 'greedy_slew',
            'exposure_time': '300',
            'filters': 'ztfg',
            'maximum_airmass': 2.0,
            'integrated_probability': 100,
            'minimum_time_difference': 30,
            'queue_name': 'ToO_Fake',
            'program_id': 'Partnership',
            'subprogram_name': 'GRB',
        },
    }

    status, data = api(
        'POST', 'observation_plan', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    # wait for the observation plan to finish
    time.sleep(15)

    status, data = api(
        'GET',
        f'observation_plan/{id}',
        params={"includePlannedObservations": "true"},
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    assert data["data"]["gcnevent_id"] == gcnevent_id
    assert data["data"]["allocation_id"] == allocation_id
    assert data["data"]["payload"] == request_data["payload"]

    assert len(data["data"]["observation_plans"]) == 1
    observation_plan = data["data"]["observation_plans"][0]

    assert observation_plan['plan_name'] == request_data["payload"]['queue_name']
    assert observation_plan['validity_window_start'] == request_data["payload"][
        'start_date'
    ].replace(" ", "T")
    assert observation_plan['validity_window_end'] == request_data["payload"][
        'end_date'
    ].replace(" ", "T")

    planned_observations = observation_plan['planned_observations']

    assert len(planned_observations) == 5
    assert all(
        [
            obs['filt'] == request_data["payload"]['filters']
            for obs in planned_observations
        ]
    )
    assert all(
        [
            obs['exposure_time'] == int(request_data["payload"]['exposure_time'])
            for obs in planned_observations
        ]
    )


@pytest.mark.flaky(reruns=2)
def test_observation_plan_galaxy(
    user, super_admin_token, upload_data_token, view_only_token, public_group
):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    gcnevent_id = data['data']['gcnevent_id']

    dateobs = "2019-04-25 08:18:05"
    skymap = "bayestar.fits.gz"
    status, data = api(
        'GET',
        f'localization/{dateobs}/name/{skymap}',
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    localization_id = data['data']['id']

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

    fielddatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv'
    regionsdatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Region.reg'

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
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            status, data = api(
                'GET',
                f'instrument/{instrument_id}',
                token=super_admin_token,
            )
            assert status == 200
            assert data['status'] == 'success'
            assert data['data']['band'] == 'NIR'

            assert len(data['data']['fields']) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    catalog_name = str(uuid.uuid4())
    datafile = f'{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5'
    data = {
        'catalog_name': catalog_name,
        'catalog_data': Table.read(datafile).to_pandas().to_dict(orient='list'),
    }

    status, data = api('POST', 'galaxy_catalog', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    params = {'catalog_name': catalog_name}

    nretries = 0
    galaxies_loaded = False
    while not galaxies_loaded and nretries < 5:
        try:
            status, data = api(
                'GET', 'galaxy_catalog', token=view_only_token, params=params
            )
            assert status == 200
            data = data["data"]["sources"]
            assert len(data) == 10
            assert any(
                [
                    d['name'] == '6dFgs gJ0001313-055904'
                    and d['mstar'] == 336.60756522868667
                    for d in data
                ]
            )
            galaxies_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(5)

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

    request_data = {
        'allocation_id': allocation_id,
        'gcnevent_id': gcnevent_id,
        'localization_id': localization_id,
        'payload': {
            'start_date': '2019-04-25 01:01:01',
            'end_date': '2019-04-27 01:01:01',
            'filter_strategy': 'block',
            'schedule_strategy': 'galaxy',
            'galaxy_catalog': catalog_name,
            'schedule_type': 'greedy_slew',
            'exposure_time': '300',
            'filters': 'ztfg',
            'maximum_airmass': 2.0,
            'integrated_probability': 100,
            'minimum_time_difference': 30,
            'queue_name': 'ToO_Fake',
            'program_id': 'Partnership',
            'subprogram_name': 'GRB',
        },
    }

    status, data = api(
        'POST', 'observation_plan', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    # wait for the observation plan to populate
    nretries = 0
    observation_plan_loaded = False
    while not observation_plan_loaded and nretries < 5:
        try:
            status, data = api(
                'GET',
                f'observation_plan/{id}',
                params={"includePlannedObservations": "true"},
                token=super_admin_token,
            )

            assert status == 200
            assert data['status'] == 'success'

            assert data["data"]["gcnevent_id"] == gcnevent_id
            assert data["data"]["allocation_id"] == allocation_id
            assert data["data"]["payload"] == request_data["payload"]

            assert len(data["data"]["observation_plans"]) == 1
            observation_plan = data["data"]["observation_plans"][0]

            assert (
                observation_plan['plan_name'] == request_data["payload"]['queue_name']
            )
            assert observation_plan['validity_window_start'] == request_data["payload"][
                'start_date'
            ].replace(" ", "T")
            assert observation_plan['validity_window_end'] == request_data["payload"][
                'end_date'
            ].replace(" ", "T")

            planned_observations = observation_plan['planned_observations']
            print(planned_observations)
            assert len(planned_observations) > 0

            observation_plan_loaded = True

        except AssertionError:
            nretries = nretries + 1
            time.sleep(10)

    assert len(planned_observations) == 6
    assert all(
        [
            obs['filt'] == request_data["payload"]['filters']
            for obs in planned_observations
        ]
    )
    assert all(
        [
            obs['exposure_time'] == int(request_data["payload"]['exposure_time'])
            for obs in planned_observations
        ]
    )
