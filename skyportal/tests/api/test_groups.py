import uuid
from skyportal.tests import api


def test_token_user_create_new_group_no_sources(manage_groups_token, user):
    group_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'groups',
        data={'name': group_name,
              'group_admins': [user.username]},
        token=manage_groups_token)
    assert status == 200
    assert data['status'] == 'success'
    new_group_id = data['data']['id']

    status, data = api('GET', f'groups/{new_group_id}',
                       token=manage_groups_token)
    assert data['status'] == 'success'
    assert data['data']['group']['name'] == group_name
    assert len(data['data']['group']['sources']) == 0


def test_token_user_create_new_group_with_source(manage_groups_token, user, public_source):
    group_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'groups',
        data={'name': group_name,
              'group_admins': [user.username],
              'source_ids': [public_source.id]},
        token=manage_groups_token)
    assert status == 200
    assert data['status'] == 'success'
    new_group_id = data['data']['id']

    status, data = api('GET', f'groups/{new_group_id}',
                       token=manage_groups_token)
    assert data['status'] == 'success'
    assert data['data']['group']['name'] == group_name
    assert len(data['data']['group']['sources']) == 1
    assert data['data']['group']['sources'][0]['id'] == public_source.id


def test_token_user_update_group(manage_groups_token, public_group):
    new_name = str(uuid.uuid4())
    status, data = api(
        'PUT',
        f'groups/{public_group.id}',
        data={'name': new_name},
        token=manage_groups_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_groups_token)
    assert data['status'] == 'success'
    assert data['data']['group']['name'] == new_name


def test_token_user_delete_group(manage_groups_token, public_group):
    status, data = api(
        'DELETE',
        f'groups/{public_group.id}',
        token=manage_groups_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_groups_token)
    assert status == 400
