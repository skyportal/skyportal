import uuid
from skyportal.tests import api
from skyportal.models import Telescope, DBSession


def test_token_user_post_get_telescope(upload_data_token):
    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'nickname': name,
        'lat': 0.0,
        'lon': 0.0,
        'elevation': 0.0,
        'diameter': 10.0,
        'skycam_link': 'http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg',
        'robotic': True,
    }

    status, data = api('POST', 'telescope', data=post_data, token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    telescope_id = data['data']['id']
    status, data = api('GET', f'telescope/{telescope_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    for key in post_data:
        assert data['data'][key] == post_data[key]


def test_fetch_telescope_by_name(upload_data_token):
    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'nickname': name,
        'lat': 0.0,
        'lon': 0.0,
        'elevation': 0.0,
        'diameter': 10.0,
        'skycam_link': 'http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg',
    }

    status, data = api('POST', 'telescope', data=post_data, token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'telescope?name={name}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']) == 1
    for key in post_data:
        assert data['data'][0][key] == post_data[key]


def test_token_user_update_telescope(upload_data_token, manage_sources_token):
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
            'robotic': True,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    telescope_id = data['data']['id']
    status, data = api('GET', f'telescope/{telescope_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['diameter'] == 10.0

    status, data = api(
        'PUT',
        f'telescope/{telescope_id}',
        data={
            'name': name,
            'nickname': name,
            'lat': 0.0,
            'lon': 0.0,
            'elevation': 0.0,
            'diameter': 12.0,
        },
        token=manage_sources_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'telescope/{telescope_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['diameter'] == 12.0


def test_token_user_delete_telescope(upload_data_token, manage_sources_token):
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
            'robotic': False,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    telescope_id = data['data']['id']
    status, data = api('GET', f'telescope/{telescope_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['diameter'] == 10.0

    status, data = api(
        'DELETE', f'telescope/{telescope_id}', token=manage_sources_token
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'telescope/{telescope_id}', token=upload_data_token)
    assert status == 400
