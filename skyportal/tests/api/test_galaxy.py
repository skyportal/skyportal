import os
import time
from astropy.table import Table
from datetime import datetime
import numpy as np
import uuid

from skyportal.tests import api, assert_api, assert_api_fail


def test_galaxy(super_admin_token, view_only_token):
    catalog_name = str(uuid.uuid4())
    dateobs = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
        unique_payload = payload.replace(b'2019-08-14T21:10:39', dateobs.encode())
    event_data = {'xml': unique_payload}

    status, data = api('POST', 'gcn_event', data=event_data, token=super_admin_token)
    assert_api(status, data)

    # wait for event to load
    for _ in range(26):
        status, data = api('GET', f"gcn_event/{dateobs}", token=super_admin_token)
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert_api(status, data)

    # wait for the localization to load
    params = {"include2DMap": True}
    for _ in range(26):
        status, data = api(
            'GET',
            f'localization/{dateobs}/name/LALInference.v1.fits.gz',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            localization = data["data"]
            assert localization["dateobs"] == dateobs
            assert localization["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(localization["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert_api(status, data)

    datafile = f'{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5'
    data = {
        'catalog_name': catalog_name,
        'catalog_data': Table.read(datafile)
        .to_pandas()
        .replace({np.nan: None})
        .to_dict(orient='list'),
    }
    status, data = api('POST', 'galaxy_catalog', data=data, token=super_admin_token)
    assert_api(status, data)

    params = {'catalog_name': catalog_name}
    for n_retries in range(40):
        status, data = api(
            'GET', 'galaxy_catalog', token=view_only_token, params=params
        )
        assert_api(status, data)
        galaxies = data["data"]["galaxies"]
        if len(galaxies) == 92 and any(
            [
                galaxy['name'] == '6dFgs gJ0001313-055904'
                and galaxy['mstar'] == 336.60756522868667
                for galaxy in galaxies
            ]
        ):
            break
        else:
            time.sleep(2)

    assert n_retries < 39

    params = {
        'includeGeoJSON': True,
        'catalog_name': catalog_name,
        'localizationDateobs': dateobs,
        'localizationCumprob': 0.45,
    }
    status, data = api('GET', 'galaxy_catalog', token=view_only_token, params=params)
    assert_api(status, data)

    geojson = data["data"]["geojson"]
    galaxies = data["data"]["galaxies"]

    # now we have restricted to only 2/92 being in localization
    assert len(galaxies) == 2
    assert any(
        [
            galaxy['name'] == 'MCG -04-03-023' and galaxy['mstar'] == 20113219211.26844
            for galaxy in galaxies
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
            g['geometry']['coordinates'] == [13.1945, -25.671583]
            and g['properties']['name'] == 'MCG -04-03-023'
            for g in geojson['features']
        ]
    )

    status, data = api(
        'DELETE', f'galaxy_catalog/{catalog_name}', token=super_admin_token
    )
    assert_api(status, data)

    params = {'catalog_name': catalog_name}
    status, data = api('GET', 'galaxy_catalog', token=view_only_token, params=params)
    assert_api_fail(status, data, 400, f'Catalog with name {catalog_name} not found')


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
