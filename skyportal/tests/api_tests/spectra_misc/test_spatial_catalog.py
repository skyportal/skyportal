import os
import time
import uuid

import pandas as pd
import pytest

from skyportal.tests import api


@pytest.mark.flaky(reruns=3)
def test_spatial_catalog(super_admin_token, upload_data_token, view_only_token):
    catalog_name = str(uuid.uuid4())

    datafile = f"{os.path.dirname(__file__)}/../data/gll_psc_v27_small.csv"
    data_out = pd.read_csv(datafile)
    entries = [str(uuid.uuid4()) for _ in range(len(data_out))]
    data_out["name"] = entries

    data = {
        "catalog_name": catalog_name,
        "catalog_data": data_out.to_dict(orient="list"),
    }

    status, data = api("POST", "spatial_catalog", data=data, token=super_admin_token)
    assert status == 200

    catalog_id = data["data"]["id"]

    # wait for catalog to load
    for n_times in range(26):
        status, data = api(
            "GET", f"spatial_catalog/{catalog_id}", token=super_admin_token
        )
        if data["status"] == "success" and len(data["data"]["entries"]) == 2:
            break
        time.sleep(2)
    assert n_times < 25

    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 33.043637,
            "dec": 53.36078,
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200

    params = {
        "spatialCatalogName": catalog_name,
        "spatialCatalogEntryName": entries[1],
    }
    status, data = api("GET", "sources", token=view_only_token, params=params)
    assert len(data["data"]["sources"]) >= 1
    assert any(source["id"] == obj_id for source in data["data"]["sources"])

    status, data = api(
        "DELETE", f"spatial_catalog/{catalog_id}", data=data, token=super_admin_token
    )
    assert status == 200

    status, data = api("GET", f"spatial_catalog/{catalog_id}", token=super_admin_token)
    assert status == 400
