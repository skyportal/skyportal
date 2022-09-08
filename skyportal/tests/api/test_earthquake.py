import os
import numpy as np

from skyportal.tests import api


def test_earthquake_quakeml(super_admin_token, view_only_token):

    datafile = f'{os.path.dirname(__file__)}/../data/quakeml.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'earthquake', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    event_id = data["data"]["id"]

    status, data = api('GET', f'earthquake/{event_id}', token=super_admin_token)
    assert status == 200
    data = data["data"]
    data = data['notices'][0]
    assert data["date"] == '2020-08-19T02:00:39'
    assert np.isclose(data["lat"], 39.3648333)
    assert np.isclose(data["lon"], -123.2506667)
    assert np.isclose(data["magnitude"], 2.93)
    assert np.isclose(data["depth"], 7380.0)

    params = {
        'startDate': "2020-01-01T00:00:00",
        'endDate': "2021-01-01T00:00:00",
    }

    status, data = api('GET', 'earthquake', token=super_admin_token, params=params)
    assert status == 200
    data = data["data"]
    assert len(data['events']) > 0
    data = data['events'][0]
    data = data['notices'][0]
    assert data["date"] == '2020-08-19T02:00:39'
    assert np.isclose(data["lat"], 39.3648333)
    assert np.isclose(data["lon"], -123.2506667)
    assert np.isclose(data["magnitude"], 2.93)
    assert np.isclose(data["depth"], 7380.0)

    params = {
        'startDate': "2021-01-01T00:00:00",
        'endDate': "2022-01-01T00:00:00",
    }

    status, data = api('GET', 'earthquake', token=super_admin_token, params=params)
    assert status == 200
    data = data["data"]
    assert len(data['events']) == 0


def test_earthquake_dictionary(super_admin_token, view_only_token):

    data = {
        'event_id': 'quakeml:nc.anss.org-Event-NC-73446401',
        'latitude': 39.3648333,
        'longitude': -123.2506667,
        'depth': 7380.0,
        'magnitude': 2.93,
        'date': '2020-08-19 02:00:39',
    }

    status, data = api('POST', 'earthquake', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    event_id = data["data"]["id"]

    status, data = api('GET', f'earthquake/{event_id}', token=super_admin_token)
    assert status == 200
    data = data["data"]
    data = data['notices'][0]
    assert data["date"] == '2020-08-19T02:00:39'

    status, data = api(
        'DELETE', f'earthquake/{event_id}', data=data, token=view_only_token
    )
    assert data['message'] == 'Earthquake event not found'
    assert status == 404

    status, data = api(
        'DELETE', f'earthquake/{event_id}', data=data, token=super_admin_token
    )
    assert data['status'] == 'success'

    status, data = api('GET', f'earthquake/{event_id}', token=super_admin_token)
    print(data)
    print(status)
