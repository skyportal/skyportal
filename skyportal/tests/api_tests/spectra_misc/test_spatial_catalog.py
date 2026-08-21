import os
import time
import uuid

import pandas as pd
import pytest
from skyportal_py import SkyPortalError
from skyportal_py.sources import SourcePost

from skyportal.tests import client


@pytest.mark.flaky(reruns=3)
def test_spatial_catalog(super_admin_token, upload_data_token, view_only_token):
    catalog_name = str(uuid.uuid4())

    datafile = f"{os.path.dirname(__file__)}/../../data/gll_psc_v27_small.csv"
    data_out = pd.read_csv(datafile)
    entries = [str(uuid.uuid4()) for _ in range(len(data_out))]
    data_out["name"] = entries

    sp_admin = client(super_admin_token)
    catalog_id = sp_admin.post_spatial_catalog(
        catalog_name, data_out.to_dict(orient="list")
    ).id

    # wait for catalog to load
    for n_times in range(26):
        catalog = sp_admin.fetch_spatial_catalog(catalog_id)
        if catalog.entries is not None and len(catalog.entries) == 2:
            break
        time.sleep(2)
    assert n_times < 25

    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=33.043637,
            dec=53.36078,
        )
    )

    client(view_only_token).fetch_source(obj_id)

    page = client(view_only_token).fetch_sources(
        spatial_catalog_name=catalog_name,
        spatial_catalog_entry_name=entries[1],
    )
    assert len(page.sources) >= 1
    assert any(source.id == obj_id for source in page.sources)

    sp_admin.delete_spatial_catalog(catalog_id)

    with pytest.raises(SkyPortalError) as err:
        sp_admin.fetch_spatial_catalog(catalog_id)
    assert err.value.status_code == 400
