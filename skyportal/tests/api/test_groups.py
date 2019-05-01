from skyportal.tests import api


def test_token_user_update_group(manage_groups_token, public_group):
    status, data = api(
        'PUT',
        f'groups/{public_group.id}',
        data={'name': 'new name'},
        token=manage_groups_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_groups_token)
    assert data['status'] == 'success'
    assert data['data']['group']['name'] == 'new name'
