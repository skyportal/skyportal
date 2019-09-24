import uuid
from skyportal.tests import api
from skyportal.model_util import create_token
from skyportal.models import DBSession, Token


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


def test_delete_user_cascades_to_tokens(manage_users_token, user, public_group):
    token_name = str(uuid.uuid4())
    token_id = create_token(group_id=public_group.id, permissions=[],
                            created_by_id=user.id, name=token_name)
    assert Token.query.get(token_id)

    status, data = api('DELETE', f'user/{user.id}', token=manage_users_token)
    assert status == 200
    assert data['data']['user_id'] == user.id

    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 400

    assert not Token.query.get(token_id)


def test_delete_user_cascades_to_groupuser(manage_users_token, manage_groups_token,
                                           user, public_group):
    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_groups_token)
    assert len(data['data']['group']['users']) == 1

    status, data = api('DELETE', f'user/{user.id}', token=manage_users_token)
    assert status == 200
    assert data['data']['user_id'] == user.id

    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 400

    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_groups_token)
    assert len(data['data']['group']['users']) == 0
