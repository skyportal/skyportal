import uuid
from skyportal.tests import api
from skyportal.models import Telescope, Instrument, DBSession


def test_token_user_post_get_instrument(upload_data_token):
    name = str(uuid.uuid4())
    status, data = api('POST', 'telescope',
                       data={'name': name,
                             'nickname': name,
                             'lat': 0.0,
                             'lon': 0.0,
                             'elevation': 0.0,
                             'diameter': 10.0
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    status, data = api('POST', 'instrument',
                       data={'name': 'instrument_name',
                             'type': 'type',
                             'band': 'V',
                             'telescope_id': telescope_id
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    instrument_id = data['data']['id']
    status, data = api(
        'GET',
        f'instrument/{instrument_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['instrument']['band'] == 'V'


def test_token_user_update_instrument(upload_data_token, manage_sources_token):
    name = str(uuid.uuid4())
    status, data = api('POST', 'telescope',
                       data={'name': name,
                             'nickname': name,
                             'lat': 0.0,
                             'lon': 0.0,
                             'elevation': 0.0,
                             'diameter': 10.0
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    status, data = api('POST', 'instrument',
                       data={'name': 'instrument_name',
                             'type': 'type',
                             'band': 'V',
                             'telescope_id': telescope_id
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    instrument_id = data['data']['id']
    status, data = api(
        'GET',
        f'instrument/{instrument_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['instrument']['band'] == 'V'

    status, data = api(
        'PUT',
        f'instrument/{instrument_id}',
        data={'name': 'new_name',
              'band': 'V',
              'type': 'type'
        },
        token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET',
        f'instrument/{instrument_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['instrument']['name'] == 'new_name'


def test_token_user_delete_instrument(upload_data_token, manage_sources_token):
    name = str(uuid.uuid4())
    status, data = api('POST', 'telescope',
                       data={'name': name,
                             'nickname': name,
                             'lat': 0.0,
                             'lon': 0.0,
                             'elevation': 0.0,
                             'diameter': 10.0
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    status, data = api('POST', 'instrument',
                       data={'name': 'instrument_name',
                             'type': 'type',
                             'band': 'V',
                             'telescope_id': telescope_id
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    status, data = api(
        'DELETE',
        f'instrument/{instrument_id}',
        token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET',
        f'instrument/{instrument_id}',
        token=upload_data_token)
    assert status == 400
