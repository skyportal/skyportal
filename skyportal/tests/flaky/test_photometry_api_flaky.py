import numpy as np

from skyportal.tests import api


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
