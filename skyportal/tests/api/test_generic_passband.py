from skyportal.tests import api


def test_token_user_post_get_generic_passband(upload_data_token):
    status, data = api(
        'POST',
        'generic_passband',
        data={'name': 'atlasc', 'min_wavelength': 4125, 'max_wavelength': 8347},
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    generic_passband_id = data['data']['id']
    status, data = api(
        'GET', f'generic_passband/{generic_passband_id}', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'


def test_token_user_delete_generic_passband(super_admin_token, view_only_token):
    status, data = api(
        'POST',
        'generic_passband',
        data={'name': 'atlasc', 'min_wavelength': 4125, 'max_wavelength': 8347},
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    generic_passband_id = data['data']['id']

    status, data = api(
        'DELETE', f'generic_passband/{generic_passband_id}', token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET', f'generic_passband/{generic_passband_id}', token=view_only_token
    )
    assert status == 400
