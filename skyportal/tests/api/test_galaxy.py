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
    data = data["data"]
    assert len(data) == 10
    assert any(
        [
            d['name'] == '6dFgs gJ0001313-055904' and d['mstar'] == 336.60756522868667
            for d in data
        ]
    )
