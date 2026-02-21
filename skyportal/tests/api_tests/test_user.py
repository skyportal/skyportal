import uuid

from skyportal.model_util import create_token
from skyportal.models import DBSession, Token
from skyportal.tests import api


def test_get_user_info(manage_users_token, user):
    status, data = api("GET", f"user/{user.id}", token=manage_users_token)
    assert status == 200
    assert data["data"]["id"] == user.id


def test_delete_user(super_admin_token, user):
    status, data = api("DELETE", f"user/{user.id}", token=super_admin_token)
    assert status == 200

    status, data = api("GET", f"user/{user.id}", token=super_admin_token)
    assert status == 400


def test_delete_user_cascades_to_tokens(super_admin_token, user, public_group):
    token_name = str(uuid.uuid4())
    token_id = create_token(ACLs=[], user_id=user.id, name=token_name)
    assert Token.query.get(token_id)

    # end the transaction on the test-side
    DBSession().commit()

    status, data = api("DELETE", f"user/{user.id}", token=super_admin_token)
    assert status == 200

    status, data = api("GET", f"user/{user.id}", token=super_admin_token)
    assert status == 400

    assert not Token.query.get(token_id)


def test_delete_user_cascades_to_groupuser(
    super_admin_token, manage_groups_token, user, public_group
):
    status, data = api("GET", f"groups/{public_group.id}", token=manage_groups_token)
    orig_num_users = len(data["data"]["users"])

    status, data = api("DELETE", f"user/{user.id}", token=super_admin_token)
    assert status == 200

    status, data = api("GET", f"user/{user.id}", token=super_admin_token)
    assert status == 400

    status, data = api("GET", f"groups/{public_group.id}", token=manage_groups_token)
    assert len(data["data"]["users"]) == orig_num_users - 1


def test_add_basic_user_info(manage_groups_token, super_admin_token):
    username = str(uuid.uuid4())
    status, data = api(
        "POST",
        "user",
        data={
            "username": username,
            "first_name": "Fritz",
            "last_name": "Marshal",
            "affiliations": ["Caltech"],
        },
        token=super_admin_token,
    )
    assert status == 200
    new_user_id = data["data"]["id"]
    status, data = api("GET", f"user/{new_user_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["first_name"] == "Fritz"
    assert data["data"]["last_name"] == "Marshal"
    assert data["data"]["affiliations"] == ["Caltech"]

    status, data = api("DELETE", f"user/{new_user_id}", token=super_admin_token)
    assert status == 200

    # add a bad phone number, expecting an error
    status, data = api(
        "POST",
        "user",
        data={"username": username, "contact_phone": "blah"},
        token=super_admin_token,
    )
    assert status == 400
    assert "Could not parse input" in data["message"]


def test_add_delete_user_adds_deletes_single_user_group(
    manage_groups_token, super_admin_user_two_groups, super_admin_token
):
    username = str(uuid.uuid4())
    status, data = api(
        "POST", "user", data={"username": username}, token=super_admin_token
    )
    assert status == 200
    new_user_id = data["data"]["id"]

    status, data = api(
        "GET", "groups?includeSingleUserGroups=true", token=manage_groups_token
    )
    assert data["status"] == "success"
    assert any(
        group["single_user_group"] and group["name"] == username
        for group in data["data"]["all_groups"]
    )

    status, data = api("DELETE", f"user/{new_user_id}", token=super_admin_token)
    assert status == 200

    status, data = api(
        "GET", "groups?includeSingleUserGroups=true", token=manage_groups_token
    )
    assert data["status"] == "success"

    assert not any(
        group["single_user_group"] and group["name"] == username
        for group in data["data"]["all_groups"]
    )


def test_add_modify_user_adds_modifies_single_user_group(
    manage_groups_token, super_admin_user_two_groups, super_admin_token
):
    username = str(uuid.uuid4())
    token_name = str(uuid.uuid4())
    status, data = api(
        "POST", "user", data={"username": username}, token=super_admin_token
    )
    assert status == 200
    new_user_id = data["data"]["id"]

    status, data = api(
        "GET", "groups?includeSingleUserGroups=true", token=manage_groups_token
    )
    assert data["status"] == "success"
    assert any(
        group["single_user_group"] and group["name"] == username
        for group in data["data"]["all_groups"]
    )

    token_id = create_token(ACLs=[], user_id=new_user_id, name=token_name)
    new_username = str(uuid.uuid4())

    status, data = api(
        "PATCH", "internal/profile", data={"username": new_username}, token=token_id
    )
    assert status == 200

    status, data = api(
        "GET", "groups?includeSingleUserGroups=true", token=manage_groups_token
    )
    assert data["status"] == "success"
    assert any(
        group["single_user_group"] and group["name"] == new_username
        for group in data["data"]["all_groups"]
    )


def test_user_list(view_only_token):
    status, data = api("GET", "user", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"


def test_user_list_filtering(view_only_token, user, view_only_user):
    # Try some simple filtering options - other options follow very similar
    # logic so just these should be decent coverage

    # Username
    status, data = api(
        "GET",
        f"user/?username={user.username}",
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["users"]) == 1
    assert data["data"]["users"][0]["id"] == user.id

    # Role
    # Make sure the result shows up among all the view_only_users provisioned across tests
    # by returning a huge page
    status, data = api(
        "GET",
        "user/?role=View+only&numPerPage=300",
        token=view_only_token,
    )
    assert status == 200
    result_user_ids = [user["id"] for user in data["data"]["users"]]
    assert view_only_user.id in result_user_ids
    assert user.id not in result_user_ids
