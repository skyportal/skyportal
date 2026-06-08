import os
import time
import uuid

import numpy as np
from astropy.table import Table

from skyportal.tests import api


def test_galaxy(super_admin_token, view_only_token, gcn_GW190814):
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    catalog_name = "test_galaxy_catalog"
    # in case the catalog already exists, delete it.
    status, data = api(
        "DELETE", f"galaxy_catalog/{catalog_name}", token=super_admin_token
    )

    datafile = f"{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5"
    data = {
        "catalog_name": catalog_name,
        "catalog_data": Table.read(datafile)
        .to_pandas()
        .replace({np.nan: None})
        .to_dict(orient="list"),
    }

    status, data = api("POST", "galaxy_catalog", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    params = {"catalog_name": catalog_name}

    nretries = 0
    galaxies_loaded = False
    while nretries < 40:
        status, data = api(
            "GET", "galaxy_catalog", token=view_only_token, params=params
        )
        assert status == 200
        data = data["data"]["galaxies"]
        if len(data) == 92 and any(
            d["name"] == "6dFgs gJ0001313-055904" and d["mstar"] == 336.60756522868667
            for d in data
        ):
            galaxies_loaded = True
            break
        nretries = nretries + 1
        time.sleep(2)

    assert nretries < 40
    assert galaxies_loaded

    params = {
        "includeGeoJSON": True,
        "catalog_name": catalog_name,
        "localizationDateobs": dateobs,
        "localizationCumprob": 0.45,
    }

    status, data = api("GET", "galaxy_catalog", token=view_only_token, params=params)
    assert status == 200

    geojson = data["data"]["geojson"]
    data = data["data"]["galaxies"]

    # now we have restricted to only 3/92 being in localization
    assert len(data) == 3
    assert any(
        d["name"] == "MCG -04-03-023" and d["mstar"] == 20113219211.26844 for d in data
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
        d["geometry"]["coordinates"] == [13.1945, -25.671583]
        and d["properties"]["name"] == "MCG -04-03-023"
        for d in geojson["features"]
    )

    status, data = api(
        "DELETE", f"galaxy_catalog/{catalog_name}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    params = {"catalog_name": catalog_name}

    status, data = api("GET", "galaxy_catalog", token=view_only_token, params=params)
    assert status == 400
    assert f"Catalog with name {catalog_name} not found" in data["message"]


def test_source_host(
    super_admin_token, upload_data_token, view_only_token, public_group
):
    catalog_name = "test_galaxy_catalog"

    # in case the catalog already exists, delete it.
    status, data = api(
        "DELETE", f"galaxy_catalog/{catalog_name}", token=super_admin_token
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

    datafile = f"{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5"
    data = {
        "catalog_name": catalog_name,
        "catalog_data": Table.read(datafile)
        .to_pandas()
        .replace({np.nan: None})
        .to_dict(orient="list"),
    }

    status, data = api("POST", "galaxy_catalog", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    params = {"catalog_name": catalog_name}

    nretries = 0
    galaxies_loaded = False
    while nretries < 40:
        status, data = api(
            "GET", "galaxy_catalog", token=view_only_token, params=params
        )
        assert status == 200
        data = data["data"]["galaxies"]
        if len(data) == 92 and any(
            d["name"] == "6dFgs gJ0001313-055904" and d["mstar"] == 336.60756522868667
            for d in data
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
    assert "GALEXASC J013719.93-331951.1" in data["data"]["galaxies"]
