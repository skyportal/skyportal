import os
import time
from astropy.table import Table
import numpy as np
import uuid

from skyportal.tests import api


def test_galaxy(super_admin_token, view_only_token):
    catalog_name = 'test_galaxy_catalog'

    # in case the catalog already exists, delete it.
    status, data = api(
        'DELETE', f'galaxy_catalog/{catalog_name}', token=super_admin_token
    )

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
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

    # wait for event to load
    for n_times in range(26):
        status, data = api(
            'GET', "gcn_event/2019-08-14T21:10:39", token=super_admin_token
        )
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
            assert data["dateobs"] == "2019-08-14T21:10:39"
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25

    datafile = f'{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5'
    data = {
        'catalog_name': catalog_name,
        'catalog_data': Table.read(datafile)
        .to_pandas()
        .replace({np.nan: None})
        .to_dict(orient='list'),
    }

    status, data = api('POST', 'galaxy_catalog', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    params = {'catalog_name': catalog_name}

    nretries = 0
    galaxies_loaded = False
    while nretries < 40:
        status, data = api(
            'GET', 'galaxy_catalog', token=view_only_token, params=params
        )
        assert status == 200
        data = data["data"]["galaxies"]
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
        time.sleep(2)

    assert nretries < 40
    assert galaxies_loaded

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

    # now we have restricted to only 2/92 being in localization
    assert len(data) == 2
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
    assert status == 400
    assert f'Catalog with name {catalog_name} not found' in data['message']


def test_source_host(
    super_admin_token, upload_data_token, view_only_token, public_group
):
    catalog_name = 'test_galaxy_catalog'

    # in case the catalog already exists, delete it.
    status, data = api(
        'DELETE', f'galaxy_catalog/{catalog_name}', token=super_admin_token
    )

    obj_id = str(uuid.uuid4())
    alias = str(uuid.uuid4())
    origin = str(uuid.uuid4())

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 24.332952,
            "dec": -33.331228,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
            "alias": [alias],
            "origin": origin,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    datafile = f'{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5'
    data = {
        'catalog_name': catalog_name,
        'catalog_data': Table.read(datafile)
        .to_pandas()
        .replace({np.nan: None})
        .to_dict(orient='list'),
    }

    status, data = api('POST', 'galaxy_catalog', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    params = {'catalog_name': catalog_name}

    nretries = 0
    galaxies_loaded = False
    while nretries < 40:
        status, data = api(
            'GET', 'galaxy_catalog', token=view_only_token, params=params
        )
        assert status == 200
        data = data["data"]["galaxies"]
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
        time.sleep(2)

    assert nretries < 40
    assert galaxies_loaded

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == obj_id
    assert 'GALEXASC J013719.93-331951.1' in data["data"]["galaxies"]
