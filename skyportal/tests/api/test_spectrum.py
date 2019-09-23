import datetime

from skyportal.tests import api


def test_token_user_post_get_spectrum_data(upload_data_token, public_source):
    status, data = api('POST', 'spectrum',
                       data={'source_id': str(public_source.id),
                             'observed_at': str(datetime.datetime.now()),
                             'instrument_id': 1,
                             'wavelengths': [664, 665, 666],
                             'fluxes': [234.2, 232.1, 235.3]
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api(
        'GET',
        f'spectrum/{spectrum_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['spectrum']['fluxes'][0] == 234.2
    assert data['data']['spectrum']['source_id'] == public_source.id


def test_token_user_post_spectrum_no_access(view_only_token, public_source):
    status, data = api('POST', 'spectrum',
                       data={'source_id': str(public_source.id),
                             'observed_at': str(datetime.datetime.now()),
                             'instrument_id': 1,
                             'wavelengths': [664, 665, 666],
                             'fluxes': [234.2, 232.1, 235.3]
                       },
                       token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'



def test_token_user_update_spectrum(upload_data_token,
                                    manage_sources_token,
                                    public_source):
    status, data = api('POST', 'spectrum',
                       data={'source_id': str(public_source.id),
                             'observed_at': str(datetime.datetime.now()),
                             'instrument_id': 1,
                             'wavelengths': [664, 665, 666],
                             'fluxes': [234.2, 232.1, 235.3]
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api(
        'GET',
        f'spectrum/{spectrum_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['spectrum']['fluxes'][0] == 234.2

    status, data = api(
        'PUT',
        f'spectrum/{spectrum_id}',
        data={'fluxes': [222.2, 232.1, 235.3],
              'observed_at': str(datetime.datetime.now()),
              'wavelengths': [664, 665, 666]},
        token=manage_sources_token)
    status, data = api(
        'GET',
        f'spectrum/{spectrum_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['spectrum']['fluxes'][0] == 222.2


def test_delete_spectrum_data(upload_data_token, manage_sources_token,
                              public_source):
    status, data = api('POST', 'spectrum',
                       data={'source_id': str(public_source.id),
                             'observed_at': str(datetime.datetime.now()),
                             'instrument_id': 1,
                             'wavelengths': [664, 665, 666],
                             'fluxes': [234.2, 232.1, 235.3]
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    spectrum_id = data['data']['id']
    status, data = api(
        'GET',
        f'spectrum/{spectrum_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['spectrum']['fluxes'][0] == 234.2
    assert data['data']['spectrum']['source_id'] == public_source.id

    status, data = api(
        'DELETE',
        f'spectrum/{spectrum_id}',
        token=manage_sources_token)
    assert status == 200

    status, data = api(
        'GET',
        f'spectrum/{spectrum_id}',
        token=upload_data_token)
    assert status == 400
