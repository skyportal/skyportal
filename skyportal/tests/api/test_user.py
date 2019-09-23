from skyportal.tests import api


def test_get_user_info(manage_users_token, user):
    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 200
    assert data['data']['user']['id'] == user.id


def test_get_user_info_access_denied(view_only_token, user):
    status, data = api('GET', f'user/{user.id}', token=view_only_token)
    assert status == 400


def test_delete_user(manage_users_token, user):
    status, data = api('DELETE', f'user/{user.id}', token=manage_users_token)
    assert status == 200
    assert data['data']['user_id'] == user.id

    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 400
