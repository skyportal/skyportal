from skyportal.tests import api
import uuid


def test_token_user_post_get_generic_passband(upload_data_token):
    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'generic_passband',
        data={'name': name, 'min_wavelength': 4125, 'max_wavelength': 8347},
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
    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'generic_passband',
        data={'name': name, 'min_wavelength': 4125, 'max_wavelength': 8347},
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


def test_token_user_update_generic_passband(
    super_admin_token, upload_data_token, view_only_token
):
    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'generic_passband',
        data={'name': name, 'min_wavelength': 4125, 'max_wavelength': 8347},
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    generic_passband_id = data['data']['id']

    status, data = api(
        'PUT',
        f'generic_passband/{generic_passband_id}',
        data={'name': name, 'min_wavelength': 3000, 'max_wavelength': 8347},
        token=super_admin_token,
    )
    print(data)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET', f'generic_passband/{generic_passband_id}', token=view_only_token
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['min_wavelength'] == 3000
