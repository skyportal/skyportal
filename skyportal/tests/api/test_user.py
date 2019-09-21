from skyportal.tests import api


def test_user_info(manage_users_token, user):
    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 200
    assert data['data']['user']['id'] == user.id


def test_user_info_access_denied(view_only_token, user):
    status, data = api('GET', f'user/{user.id}', token=view_only_token)
    assert status == 400
