import uuid
from skyportal.tests import api
from skyportal.model_util import create_token
from skyportal.models import DBSession, Token


def test_get_user_info(manage_users_token, user):
    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 200
    assert data['data']['id'] == user.id


def test_get_user_info_access_denied(view_only_token, user):
    status, data = api('GET', f'user/{user.id}', token=view_only_token)
    assert status == 400


def test_delete_user(manage_users_token, user):
    status, data = api('DELETE', f'user/{user.id}', token=manage_users_token)
    assert status == 200

    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 400


def test_delete_user_cascades_to_tokens(manage_users_token, user, public_group):
    token_name = str(uuid.uuid4())
    token_id = create_token(ACLs=[], user_id=user.id,
                            name=token_name)
    assert Token.query.get(token_id)

    # end the transaction on the test-side
    DBSession().commit()

    status, data = api('DELETE', f'user/{user.id}', token=manage_users_token)
    assert status == 200

    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 400

    assert not Token.query.get(token_id)


def test_delete_user_cascades_to_groupuser(manage_users_token, manage_groups_token,
                                           user, public_group):
    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_groups_token)
    orig_num_users = len(data['data']['users'])

    status, data = api('DELETE', f'user/{user.id}', token=manage_users_token)
    assert status == 200

    status, data = api('GET', f'user/{user.id}', token=manage_users_token)
    assert status == 400

    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_groups_token)
    assert len(data['data']['users']) == orig_num_users - 1


def test_add_basic_user_info(manage_groups_token, manage_users_token):

    username = str(uuid.uuid4())
    status, data = api(
        "POST", "user", data={"username": username, "first_name": "Fritz"},
        token=manage_users_token
    )
    assert status == 200
    new_user_id = data["data"]["id"]
    status, data = api('GET', f'user/{new_user_id}', token=manage_users_token)
    assert status == 200
    assert data["data"]["first_name"] == "Fritz"

    status, data = api('DELETE', f'user/{new_user_id}',
                       token=manage_users_token)
    assert status == 200

    # add a bad phone number, expecting an error
    status, data = api(
        "POST", "user", data={"username": username, "contact_phone": "blah"},
        token=manage_users_token
    )
    assert status == 400
    assert "did not seem to be a phone number" in data["message"]


def test_add_delete_user_adds_deletes_single_user_group(
        manage_groups_token, super_admin_user_two_groups, manage_users_token
):
    username = str(uuid.uuid4())
    status, data = api(
        "POST", "user", data={"username": username},
        token=manage_users_token
    )
    assert status == 200
    new_user_id = data["data"]["id"]

    status, data = api(
        "GET", "groups?includeSingleUserGroups=true", token=manage_groups_token
    )
    assert data["status"] == "success"
    assert any(
        [
            group["single_user_group"] == True
            and group["name"] == username
            for group in data["data"]["all_groups"]
        ]
    )

    status, data = api('DELETE', f'user/{new_user_id}',
                       token=manage_users_token)
    assert status == 200

    status, data = api(
        "GET", "groups?includeSingleUserGroups=true", token=manage_groups_token
    )
    assert data["status"] == "success"
    assert not any(
        [
            group["single_user_group"] == True
            and group["name"] == username
            for group in data["data"]["all_groups"]
        ]
    )
