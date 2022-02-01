import os
import time
from astropy.table import Table

from skyportal.tests import api


def test_galaxy(super_admin_token, view_only_token):

    datafile = f'{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5'
    data = {
        'catalog_name': 'CLU_mini',
        'catalog_data': Table.read(datafile).to_pandas().to_dict(orient='list'),
    }

    status, data = api('POST', 'galaxy_catalog', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for galaxies to load
    time.sleep(15)

    status, data = api('GET', 'galaxy_catalog', token=view_only_token)
    assert status == 200
    data = data["data"]["sources"]
    assert len(data) == 10
    assert any(
        [
            d['name'] == '6dFgs gJ0001313-055904' and d['mstar'] == 336.60756522868667
            for d in data
        ]
    )

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for tiles to load
    time.sleep(15)

    params = {
        'includeGeojson': True,
        'localizationDateobs': '2019-04-25T08:18:05',
        'localizationCumprob': 0.8,
    }

    status, data = api('GET', 'galaxy_catalog', token=view_only_token, params=params)
    assert status == 200

    geojson = data["data"]["geojson"]
    data = data["data"]["sources"]

    # now we have restricted to only 2/10 being in localization
    assert len(data) == 2
    assert any(
        [
            d['name'] == '2MASX J00022478-5445592' and d['mstar'] == 14329555096.85143
            for d in data
        ]
    )

    # The GeoJSON takes the form of
    """
    [{"geometry": {"coordinates": [0.60321, -54.76653], "type": "Point"}, "properties": {"name": "2MASX J00022478-5445592"}, "type": "Feature"}, {"geometry": {"coordinates": [0.948375, -54.574083], "type": "Point"}, "properties": {"name": "IRAS F00012-5451 ID"}, "type": "Feature"}]
    """

    assert any(
        [
            d['geometry']['coordinates'] == [0.60321, -54.76653]
            and d['properties']['name'] == '2MASX J00022478-5445592'
            for d in geojson
        ]
    )
