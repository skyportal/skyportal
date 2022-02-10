import os
import numpy as np
import pandas as pd
import time
from regions import Regions

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
        'telescopeName': name,
        'instrumentName': instrument_name,
        'observationData': pd.read_csv(datafile).to_dict(orient='list'),
    }

    status, data = api('POST', 'observation', data=data, token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'

    # wait for the executed observations to populate
    time.sleep(15)

    data = {
        'telescopeName': name,
        'instrumentName': instrument_name,
        'startDate': "2019-04-25 08:18:05",
        'endDate': "2019-04-28 08:18:05",
        'localizationDateobs': "2019-04-25T08:18:05",
        'localizationName': "bayestar.fits.gz",
        'localizationCumprob': 1.01,
        'returnStatistics': True,
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
        'telescopeName': name,
        'instrumentName': instrument_name,
        'startDate': "2019-04-25 08:18:05",
        'endDate': "2019-04-28 08:18:05",
        'localizationDateobs': "2019-04-25T08:18:05",
        'localizationName': "bayestar.fits.gz",
        'localizationCumprob': 1.01,
        'returnStatistics': True,
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
