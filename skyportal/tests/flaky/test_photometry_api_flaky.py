import numpy as np
import os
import pandas as pd
import uuid

from skyportal.tests import api
from skyportal.handlers.api.photometry import add_external_photometry


def test_token_user_big_post(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': [58000 + i for i in range(30000)],
            'instrument_id': ztf_camera.id,
            'mag': np.random.uniform(low=18, high=22, size=30000).tolist(),
            'magerr': np.random.uniform(low=0.1, high=0.3, size=30000).tolist(),
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'


def test_post_external_photometry(
    upload_data_token, super_admin_token, super_admin_user, public_group
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': name,
            'nickname': name,
            'lat': 0.0,
            'lon': 0.0,
            'elevation': 0.0,
            'diameter': 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    instrument_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name,
            'type': 'imager',
            'band': 'NIR',
            'filters': ['atlaso', 'atlasc'],
            'telescope_id': telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    datafile = f'{os.path.dirname(__file__)}/../data/ZTFrlh6cyjh_ATLAS.csv'
    df = pd.read_csv(datafile)
    df.drop(columns=['index'], inplace=True)

    data_out = {
        'obj_id': obj_id,
        'instrument_id': instrument_id,
        'group_ids': 'all',
        **df.to_dict(orient='list'),
    }

    add_external_photometry(data_out, super_admin_user)

    # Check the photometry sent back with the source
    status, data = api(
        "GET",
        f"sources/{obj_id}",
        params={"includePhotometry": "true"},
        token=super_admin_token,
    )
    assert status == 200
    assert len(data["data"]["photometry"]) == 384

    assert all(p['obj_id'] == obj_id for p in data["data"]["photometry"])
    assert all(p['instrument_id'] == instrument_id for p in data["data"]["photometry"])
