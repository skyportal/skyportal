import os
import uuid
import time
from astropy.table import Table
import numpy as np

from skyportal.tests import api


def delete_galaxy(token, catalog_name):
    status, data = api('DELETE', f'galaxy_catalog/{catalog_name}', token=token)
    assert status == 200
    assert data['status'] == 'success'


def test_galaxy(super_admin_token, view_only_token):

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
    while nretries < 10:
        status, data = api(
            'GET', 'galaxy_catalog', token=view_only_token, params=params
        )
        assert status == 200
        data = data["data"]["galaxies"]
        print(f"{len(data)} galaxies loaded")
        if len(data) == 92 and any(
            [
                d['name'] == '6dFgs gJ0001313-055904'
                and d['mstar'] == 336.60756522868667
                for d in data
            ]
        ):
            galaxies_loaded = True
            break
        nretries = nretries + 1
        time.sleep(5)

    if not nretries < 10 or not galaxies_loaded:
        delete_galaxy(super_admin_token, catalog_name)
        assert nretries < 10
        assert galaxies_loaded

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for event to load
    for n_times in range(26):
        status, data = api(
            'GET', "gcn_event/2019-08-14T21:10:39", token=super_admin_token
        )
        if data['status'] == 'success':
            break
        time.sleep(2)
    if not n_times < 25:
        delete_galaxy(super_admin_token, catalog_name)
        assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}
    for n_times_2 in range(26):
        status, data = api(
            'GET',
            f'localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            data = data["data"]
            assert data["dateobs"] == "2019-08-14T21:10:39"
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    if not n_times_2 < 25:
        delete_galaxy(super_admin_token, catalog_name)
        assert n_times_2 < 25

    params = {
        'includeGeoJSON': True,
        'catalog_name': catalog_name,
        'localizationDateobs': '2019-08-14T21:10:39',
        'localizationCumprob': 0.45,
    }

    status, data = api('GET', 'galaxy_catalog', token=view_only_token, params=params)
    assert status == 200

    geojson = data["data"]["geojson"]
    data = data["data"]["galaxies"]
    # for galaxy in data:
    #     print(galaxy)

    for element in geojson:
        print(geojson[element])

    # now we have restricted to only 3/92 being in localization
    if not len(data) == 3 or not any(
        [
            d['name'] == 'MCG -04-03-023' and d['mstar'] == 20113219211.26844
            for d in data
        ]
    ):
        delete_galaxy(super_admin_token, catalog_name)
        assert len(data) == 3
        assert any(
            [
                d['name'] == 'MCG -04-03-023' and d['mstar'] == 20113219211.26844
                for d in data
            ]
        )

    # The GeoJSON takes the form of
    """
    [
        {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [13.1945, -25.671583]}, 'properties': {'name': 'MCG -04-03-023'}},
        {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [13.309667, -25.613972]}, 'properties': {'name': '2dFGRS S144Z036'}},
        {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [11.888002, -25.28822]}, 'properties': {'name': 'NGC 0253'}}
    ]
    """

    if not any(
        [
            d['geometry']['coordinates'] == [13.1945, -25.671583]
            and d['properties']['name'] == 'MCG -04-03-023'
            for d in geojson['features']
        ]
    ):
        delete_galaxy(super_admin_token, catalog_name)
        assert any(
            [
                d['geometry']['coordinates'] == [13.1945, -25.671583]
                and d['properties']['name'] == 'MCG -04-03-023'
                for d in geojson['features']
            ]
        )

    status, data = api(
        'DELETE', f'galaxy_catalog/{catalog_name}', token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    params = {'catalog_name': catalog_name}

    status, data = api('GET', 'galaxy_catalog', token=view_only_token, params=params)
    assert status == 200
    data = data["data"]["galaxies"]
    assert len(data) == 0
