import os
import pandas as pd
import time

import uuid
from skyportal.tests import api


def test_observation(super_admin_token, view_only_token):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

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

    datafile = f'{os.path.dirname(__file__)}/../../../data/input/ZTF_Fields.csv'

    instrument_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name,
            'type': 'imager',
            'band': 'NIR',
            'filters': ['f110w'],
            'telescope_id': telescope_id,
            'field_data': pd.read_csv(datafile).iloc[:10].to_dict(orient='list'),
            'field_of_view_shape': "square",
            'field_of_view_size': 6.83,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # wait for the fields to populate
    time.sleep(15)

    datafile = f'{os.path.dirname(__file__)}/../../../data/sample_observation_data.csv'
    data = {
        'telescope_name': name,
        'instrument_name': instrument_name,
        'observation_data': pd.read_csv(datafile).to_dict(orient='list'),
    }

    status, data = api('POST', 'observation', data=data, token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'

    data = {
        'telescope_name': name,
        'instrument_name': instrument_name,
        'start_date': "2019-04-25 08:18:05",
        'end_date': "2019-04-28 08:18:05",
        'dateobs': "2019-04-25T08:18:05",
        'localization_name': "bayestar.fits.gz",
    }

    status, data = api('GET', 'observation', data=data, token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert len(data) == 10

    data = {
        'telescope_name': name,
        'instrument_name': instrument_name,
        'start_date': "2019-04-25 08:18:05",
        'end_date': "2019-04-28 08:18:05",
        'dateobs': "2019-04-25T08:18:05",
        'localization_name': "bayestar.fits.gz",
        'localization_cumprob': 1e-4,
    }

    status, data = api('GET', 'observation', data=data, token=super_admin_token)
    assert status == 200
    data = data["data"]
    # field in sample observation not within cumulative probability
    assert len(data) == 0
