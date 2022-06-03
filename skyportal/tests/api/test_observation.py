import os
import numpy as np
import pandas as pd
import time
from regions import Regions
import pytest

import uuid
from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_observation(super_admin_token, view_only_token):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    telescope_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': telescope_name,
            'nickname': telescope_name,
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
            'field_data': pd.read_csv(fielddatafile)[:5].to_dict(orient='list'),
            'field_region': Regions.read(regionsdatafile).serialize(format='ds9'),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # wait for the fields to populate
    time.sleep(15)

    datafile = f'{os.path.dirname(__file__)}/../../../data/sample_observation_data.csv'
    data = {
        'telescopeName': telescope_name,
        'instrumentName': instrument_name,
        'observationData': pd.read_csv(datafile).to_dict(orient='list'),
    }

    status, data = api('POST', 'observation', data=data, token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'

    # wait for the executed observations to populate
    time.sleep(15)

    data = {
        'telescopeName': telescope_name,
        'instrumentName': instrument_name,
        'startDate': "2019-04-25 08:18:05",
        'endDate': "2019-04-28 08:18:05",
        'localizationDateobs': "2019-04-25T08:18:05",
        'localizationName': "bayestar.fits.gz",
        'localizationCumprob': 1.01,
        'returnStatistics': True,
        'numPerPage': 1000,
    }

    status, data = api('GET', 'observation', params=data, token=super_admin_token)

    assert status == 200
    data = data["data"]
    assert len(data['observations']) == 10
    assert np.isclose(data['probability'], 2.927898964006069e-05)
    assert any(
        [
            d['obstime'] == '2019-04-25T08:18:18.002909'
            and d['observation_id'] == 84434604
            for d in data['observations']
        ]
    )

    for d in data['observations']:
        if d['observation_id'] == 84434604:
            observation_id = d['id']
            break

    status, data = api(
        'DELETE', f'observation/{observation_id}', token=super_admin_token
    )
    assert status == 200

    data = {
        'telescopeName': telescope_name,
        'instrumentName': instrument_name,
        'startDate': "2019-04-25 08:18:05",
        'endDate': "2019-04-28 08:18:05",
        'localizationDateobs': "2019-04-25T08:18:05",
        'localizationName': "bayestar.fits.gz",
        'localizationCumprob': 1.01,
        'returnStatistics': True,
        'numPerPage': 1000,
    }

    status, data = api('GET', 'observation', params=data, token=super_admin_token)
    assert status == 200
    data = data["data"]

    assert len(data['observations']) == 9
    assert not any(
        [
            d['obstime'] == '2019-04-25T08:18:18.002909'
            and d['observation_id'] == 84434604
            for d in data['observations']
        ]
    )


@pytest.mark.flaky(reruns=2)
def test_observation_radec(super_admin_token, view_only_token):

    telescope_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': telescope_name,
            'nickname': telescope_name,
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
                'GET', f'instrument/{instrument_id}', token=super_admin_token
            )
            assert status == 200
            assert data['status'] == 'success'
            assert data['data']['band'] == 'NIR'

            assert len(data['data']['fields']) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    datafile = (
        f'{os.path.dirname(__file__)}/../../../data/sample_observation_data_radec.csv'
    )
    data = {
        'telescopeName': telescope_name,
        'instrumentName': instrument_name,
        'observationData': pd.read_csv(datafile).to_dict(orient='list'),
    }

    status, data = api('POST', 'observation', data=data, token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'

    params = {
        'startDate': "2019-04-25 08:18:05",
        'endDate': "2019-04-28 08:18:05",
    }

    # wait for the executed observations to populate
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            status, data = api(
                'GET', 'observation', params=params, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data) == 10
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    assert any(
        [
            d['obstime'] == '2019-04-25T08:18:18.002909'
            and d['observation_id'] == 94434604
            for d in data['observations']
        ]
    )


@pytest.mark.flaky(reruns=2)
def test_observation_isot(super_admin_token, view_only_token):

    telescope_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': telescope_name,
            'nickname': telescope_name,
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
                'GET', f'instrument/{instrument_id}', token=super_admin_token
            )
            assert status == 200
            assert data['status'] == 'success'
            assert data['data']['band'] == 'NIR'

            assert len(data['data']['fields']) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    datafile = (
        f'{os.path.dirname(__file__)}/../../../data/sample_observation_data_isot.csv'
    )
    data = {
        'telescopeName': telescope_name,
        'instrumentName': instrument_name,
        'observationData': pd.read_csv(datafile).to_dict(orient='list'),
    }

    status, data = api('POST', 'observation', data=data, token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'

    params = {
        'startDate': "2019-04-25 08:18:05",
        'endDate': "2019-04-28 08:18:05",
    }

    # wait for the executed observations to populate
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            status, data = api(
                'GET', 'observation', params=params, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data) == 10
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    assert any(
        [
            d['obstime'] == '2019-04-25T08:18:18' and d['observation_id'] == 94434604
            for d in data['observations']
        ]
    )
