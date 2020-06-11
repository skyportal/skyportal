import uuid
from skyportal.tests import api
from skyportal.models import Telescope, Instrument, DBSession


def test_token_user_post_get_instrument(super_admin_token, public_group):
    name = str(uuid.uuid4())
    status, data = api('POST', 'telescope',
                       data={'name': name,
                             'nickname': name,
                             'lat': 0.0,
                             'lon': 0.0,
                             'elevation': 0.0,
                             'diameter': 10.0,
                             'group_ids': [public_group.id]
                             },
                       token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    status, data = api('POST', 'instrument',
                       data={'name': 'Gattini',
                             'type': 'imager',
                             'robotic': True,
                             'band': 'NIR',
                             'filters': ['f110w'],
                             'telescope_id': telescope_id
                             },
                       token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    instrument_id = data['data']['id']
    status, data = api(
        'GET',
        f'instrument/{instrument_id}',
        token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['band'] == 'NIR'


def test_token_user_update_instrument(super_admin_token, manage_sources_token,
                                      view_only_token, public_group):
    name = str(uuid.uuid4())
    status, data = api('POST', 'telescope',
                       data={'name': name,
                             'nickname': name,
                             'lat': 0.0,
                             'lon': 0.0,
                             'elevation': 0.0,
                             'diameter': 10.0,
                             'group_ids': [public_group.id]
                             },
                       token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    status, data = api('POST', 'instrument',
                       data={'name': 'Gattini',
                             'type': 'imager',
                             'robotic': True,
                             'band': 'NIR',
                             'filters': ['f110w'],
                             'telescope_id': telescope_id
                             },
                       token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    instrument_id = data['data']['id']
    status, data = api(
        'GET',
        f'instrument/{instrument_id}',
        token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['band'] == 'NIR'

    status, data = api(
        'PUT',
        f'instrument/{instrument_id}',
        data={'name': 'Gattini2',
              'type': 'imager',
              'robotic': True,
              'band': 'NIR',
              'filters': ['f110w'],
              'telescope_id': telescope_id
              },
        token=manage_sources_token)
    assert status == 400
    assert data['status'] == 'error'

    status, data = api(
        'PUT',
        f'instrument/{instrument_id}',
        data={'name': 'Gattini2',
              'type': 'imager',
              'robotic': True,
              'band': 'NIR',
              'filters': ['f110w'],
              'telescope_id': telescope_id
              },
        token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET',
        f'instrument/{instrument_id}',
        token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['name'] == 'Gattini2'


def test_token_user_delete_instrument(super_admin_token, view_only_token,
                                      public_group):
    name = str(uuid.uuid4())
    status, data = api('POST', 'telescope',
                       data={'name': name,
                             'nickname': name,
                             'lat': 0.0,
                             'lon': 0.0,
                             'elevation': 0.0,
                             'diameter': 10.0,
                             'group_ids': [public_group.id]
                             },
                       token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    status, data = api('POST', 'instrument',
                       data={'name': 'Gattini',
                             'type': 'imager',
                             'robotic': True,
                             'band': 'NIR',
                             'filters': ['f110w'],
                             'telescope_id': telescope_id
                             },
                       token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    status, data = api(
        'DELETE',
        f'instrument/{instrument_id}',
        token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET',
        f'instrument/{instrument_id}',
        token=view_only_token)
    assert status == 400
