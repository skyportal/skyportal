import os
from skyportal.tests import api
from glob import glob
from astropy.io import fits
import numpy as np
import datetime
import base64


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


def test_post_fits_spectrum(
    upload_data_token, manage_sources_token, public_source, public_group
):
    for filename in glob(f'{os.path.dirname(__file__)}/../data/ZTF*.fits'):
        with open(filename, 'rb') as f:
            status, data = api(
                'POST',
                'spectrum/fits',
                data={
                    'obj_id': str(public_source.id),
                    'observed_at': str(datetime.datetime.now()),
                    'instrument_id': 1,
                    'group_ids': [public_group.id],
                    'fluxerr_colindex': 3
                    if 'ZTF20abpuxna_20200915_Keck1_v1.ascii' in filename
                    else 2,
                    'bytestring': base64.b64encode(f.read()),
                    'filename': filename,
                },
                token=upload_data_token,
            )
        assert status == 200
        assert data['status'] == 'success'
        new_id = data['data']['id']

        with fits.open(filename) as hdul:
            header = hdul[0].header
            table_data = hdul[0].data

        status, data = api('GET', f'spectrum/{new_id}', token=upload_data_token,)

        assert status == 200
        assert data['status'] == 'success'

        header_response = data['data']['altdata']

        # check the header serialization
        for key in header_response:
            # special keys
            if key not in ['COMMENT', 'END', 'HISTORY']:
                if isinstance(data['data']['altdata'][key], dict):
                    value = data['data']['altdata'][key]['value']
                else:
                    value = data['data']['altdata'][key]
                if isinstance(header[key], (str, int)):
                    assert str(value) == str(header[key])
                elif isinstance(header[key], datetime.datetime):
                    assert datetime.datetime.fromisoformat(value) == header[key]
                elif isinstance(header[key], datetime.date):
                    assert datetime.datetime.fromisoformat(value).date() == header[key]
                elif header[key] is None:
                    assert value is None
                else:
                    np.testing.assert_allclose(value, header[key])

        # check the data serialization
        np.testing.assert_allclose(
            table_data[:, 0], np.asarray(data['data']['wavelengths'], dtype=float)
        )
        np.testing.assert_allclose(
            table_data[:, 1], np.asarray(data['data']['fluxes'], dtype=float)
        )
        np.testing.assert_allclose(
            table_data[:, 2], np.asarray(data['data']['errors'], dtype=float)
        )
