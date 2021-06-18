import os
import numpy as np

from skyportal.tests import api


def test_gcn(super_admin_token):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('PUT', 'gcn/upload', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    dateobs = "2019-04-25 08:18:05"
    status, data = api(
        'GET', f'gcn/event/{dateobs}', data=data, token=super_admin_token
    )
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2019-04-25T08:18:05"
    assert 'GW' in data["tags"]

    skymap = "bayestar.fits.gz"
    status, data = api(
        'GET',
        f'gcn/localization/{dateobs}/name/{skymap}',
        data=data,
        token=super_admin_token,
    )

    data = data["data"]
    assert data["dateobs"] == "2019-04-25T08:18:05"
    assert data["localization_name"] == "bayestar.fits.gz"
    assert np.isclose(np.sum(data["flat_2d"]), 1)

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('PUT', 'gcn/upload', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    dateobs = "2018-01-16 00:36:53"
    status, data = api(
        'GET', f'gcn/event/{dateobs}', data=data, token=super_admin_token
    )
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2018-01-16T00:36:53"
    assert 'GRB' in data["tags"]

    skymap = "214.74000_28.14000_11.19000"
    status, data = api(
        'GET',
        f'gcn/localization/{dateobs}/name/{skymap}',
        data=data,
        token=super_admin_token,
    )

    data = data["data"]
    assert data["dateobs"] == "2018-01-16T00:36:53"
    assert data["localization_name"] == "214.74000_28.14000_11.19000"
    assert np.isclose(np.sum(data["flat_2d"]), 1)
