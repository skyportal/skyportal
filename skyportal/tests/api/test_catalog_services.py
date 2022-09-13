import numpy as np
import pytest
import time
import uuid

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_swift_lsxps(super_admin_token):

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
            'filters': ['swiftxrt'],
            'telescope_id': telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        "POST",
        "catalogs/swift_lsxps",
        data={'telescope_name': name},
        token=super_admin_token,
    )
    assert status == 200

    NRETRIES = 10
    retries = 0

    sources_loaded = False
    obj_id = "Swift-J023017.0+283603"
    while not sources_loaded and retries < NRETRIES:
        status, data = api(
            'GET',
            f'sources/{obj_id}',
            token=super_admin_token,
        )
        if not status == 200:
            retries = retries + 1
            time.sleep(10)
        else:
            sources_loaded = True

    assert np.isclose(data['data']['ra'], 37.5712185545)
    assert np.isclose(data['data']['dec'], 28.6012172159)
