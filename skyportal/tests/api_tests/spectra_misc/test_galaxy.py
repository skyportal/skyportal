import contextlib
import os
import time
import uuid

import numpy as np
import pytest
from astropy.table import Table
from skyportal_py import SkyPortalError
from skyportal_py.galaxies import GalaxyCatalogPost
from skyportal_py.sources import SourcePost

from skyportal.tests import client


def test_galaxy(super_admin_token, view_only_token, gcn_GW190814):
    sp_admin = client(super_admin_token)
    sp_view = client(view_only_token)
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    catalog_name = "test_galaxy_catalog"
    # in case the catalog already exists, delete it.
    with contextlib.suppress(SkyPortalError):
        sp_admin.delete_galaxy_catalog(catalog_name)

    datafile = f"{os.path.dirname(__file__)}/../../../../data/CLU_mini.hdf5"
    catalog_data = (
        Table.read(datafile).to_pandas().replace({np.nan: None}).to_dict(orient="list")
    )

    sp_admin.post_galaxy_catalog(
        GalaxyCatalogPost(catalog_name=catalog_name, catalog_data=catalog_data)
    )

    nretries = 0
    galaxies_loaded = False
    while nretries < 40:
        galaxies = sp_view.fetch_galaxies(catalog_name=catalog_name).galaxies
        if len(galaxies) == 92 and any(
            g.name == "6dFgs gJ0001313-055904" and g.mstar == 336.60756522868667
            for g in galaxies
        ):
            galaxies_loaded = True
            break
        nretries = nretries + 1
        time.sleep(2)

    assert nretries < 40
    assert galaxies_loaded

    page = sp_view.fetch_galaxies(
        catalog_name=catalog_name,
        include_geojson=True,
        localization_dateobs=dateobs,
        localization_cumprob=0.45,
    )

    geojson = page.geojson
    galaxies = page.galaxies

    # now we have restricted to only 3/92 being in localization
    assert len(galaxies) == 3
    assert any(
        g.name == "MCG -04-03-023" and g.mstar == 20113219211.26844 for g in galaxies
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

    sp_admin.delete_galaxy_catalog(catalog_name)

    with pytest.raises(
        SkyPortalError, match=f"Catalog with name {catalog_name} not found"
    ) as err:
        sp_view.fetch_galaxies(catalog_name=catalog_name)
    assert err.value.status_code == 400


def test_source_host(
    super_admin_token, upload_data_token, view_only_token, public_group
):
    sp_admin = client(super_admin_token)
    sp_view = client(view_only_token)
    catalog_name = "test_galaxy_catalog"

    # in case the catalog already exists, delete it.
    with contextlib.suppress(SkyPortalError):
        sp_admin.delete_galaxy_catalog(catalog_name)

    obj_id = str(uuid.uuid4())
    alias = str(uuid.uuid4())
    origin = str(uuid.uuid4())

    resp = client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=24.332952,
            dec=-33.331228,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
            alias=[alias],
            origin=origin,
        )
    )
    assert resp.id == obj_id

    datafile = f"{os.path.dirname(__file__)}/../../../../data/CLU_mini.hdf5"
    catalog_data = (
        Table.read(datafile).to_pandas().replace({np.nan: None}).to_dict(orient="list")
    )

    sp_admin.post_galaxy_catalog(
        GalaxyCatalogPost(catalog_name=catalog_name, catalog_data=catalog_data)
    )

    nretries = 0
    galaxies_loaded = False
    while nretries < 40:
        galaxies = sp_view.fetch_galaxies(catalog_name=catalog_name).galaxies
        if len(galaxies) == 92 and any(
            g.name == "6dFgs gJ0001313-055904" and g.mstar == 336.60756522868667
            for g in galaxies
        ):
            galaxies_loaded = True
            break
        nretries = nretries + 1
        time.sleep(2)

    assert nretries < 40
    assert galaxies_loaded

    source = sp_view.fetch_source(obj_id)
    assert source.id == obj_id
    assert "GALEXASC J013719.93-331951.1" in source.galaxies
