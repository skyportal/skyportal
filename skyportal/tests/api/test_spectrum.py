import datetime
import os
from skyportal.tests import api
from glob import glob
import yaml
import numpy as np

import pdb


def test_token_user_post_get_spectrum_data(
    upload_data_token, public_source, public_group
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': 1,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2
    assert data['data']['obj_id'] == public_source.id


def test_token_user_post_spectrum_no_access(
    view_only_token, public_source, public_group
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': 1,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=view_only_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_update_spectrum(
    upload_data_token, manage_sources_token, public_source, public_group
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': 1,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2

    status, data = api(
        'PUT',
        f'spectrum/{spectrum_id}',
        data={
            'fluxes': [222.2, 232.1, 235.3],
            'observed_at': str(datetime.datetime.now()),
            'wavelengths': [664, 665, 666],
        },
        token=manage_sources_token,
    )
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 222.2


def test_delete_spectrum_data(
    upload_data_token, manage_sources_token, public_source, public_group
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': 1,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['fluxes'][0] == 234.2
    assert data['data']['obj_id'] == public_source.id

    status, data = api('DELETE', f'spectrum/{spectrum_id}', token=manage_sources_token)
    assert status == 200

    status, data = api('GET', f'spectrum/{spectrum_id}', token=upload_data_token)
    assert status == 400


def test_jsonify_spectrum_header(
    upload_data_token, manage_sources_token, public_source, public_group
):
    pdb.set_trace()
    for filename in glob(f'{os.path.dirname(__file__)}/../data/ZTF*.ascii.head'):
        with open(filename[:-5], 'r') as f:
            status, data = api(
                'POST',
                'spectrum/ascii',
                data={
                    'obj_id': str(public_source.id),
                    'observed_at': str(datetime.datetime.now()),
                    'instrument_id': 1,
                    'group_ids': [public_group.id],
                    'fluxerr_colindex': 3
                    if 'ZTF20abpuxna_20200915_Keck1_v1.ascii' in filename
                    else 2,
                    'ascii': f.read(),
                    'filename': filename,
                },
                token=upload_data_token,
            )
        assert status == 200
        assert data['status'] == 'success'

        answer = yaml.load(open(filename, 'r'), Loader=yaml.FullLoader)

        # check the header serialization
        for key in answer:
            # special keys
            if key not in ['COMMENT', 'END', 'HISTORY']:
                if isinstance(data['data']['altdata'][key], dict):
                    value = data['data']['altdata'][key]['value']
                else:
                    value = data['data']['altdata'][key]
                if isinstance(answer[key], (str, int)):
                    assert value == answer[key]
                else:
                    np.testing.assert_allclose(value, answer[key])


def test_jsonify_spectrum_data(
    upload_data_token, manage_sources_token, public_source, public_group
):
    for filename in glob(f'{os.path.dirname(__file__)}/../data/ZTF*.ascii'):
        with open(filename, 'r') as f:
            status, data = api(
                'POST',
                'spectrum/ascii',
                data={
                    'obj_id': str(public_source.id),
                    'observed_at': str(datetime.datetime.now()),
                    'instrument_id': 1,
                    'group_ids': [public_group.id],
                    'fluxerr_colindex': 3
                    if 'ZTF20abpuxna_20200915_Keck1_v1.ascii' in filename
                    else 2,
                    'ascii': f.read(),
                    'filename': filename,
                },
                token=upload_data_token,
            )
        assert status == 200
        assert data['status'] == 'success'

        answer = np.genfromtxt(filename, dtype=float, encoding='ascii')

        if answer.shape[-1] == 2:
            np.testing.assert_allclose(
                np.asarray(data['data']['wavelengths'], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['fluxes'], dtype=float), answer[:, 1]
            )

        elif answer.shape[-1] == 3:
            np.testing.assert_allclose(
                np.asarray(data['data']['wavelengths'], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['fluxes'], dtype=float), answer[:, 1]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['errors'], dtype=float), answer[:, 2]
            )

        else:
            # this is the long one from Keck
            np.testing.assert_allclose(
                np.asarray(data['data']['wavelengths'], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['fluxes'], dtype=float), answer[:, 1]
            )
            np.testing.assert_allclose(
                np.asarray(data['data']['errors'], dtype=float), answer[:, 3]
            )
