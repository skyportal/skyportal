from skyportal.tests import api


def test_user_info(manage_users_token):
    status, data = api('GET', 'user/1', token=manage_users_token)
    assert status == 200
    assert data['data']['user']['id'] == 1


def test_user_info_access_denied(view_only_token):
    status, data = api('GET', 'user/1', token=view_only_token)
    assert status == 400
