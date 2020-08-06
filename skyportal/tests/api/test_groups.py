import uuid
from skyportal.tests import api
from skyportal.model_util import create_token


def test_token_user_create_new_group(manage_groups_token, super_admin_user):
    group_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [super_admin_user.username]},
        token=manage_groups_token,
    )
    assert status == 200
    assert data["status"] == "success"
    new_group_id = data["data"]["id"]

    status, data = api("GET", f"groups/{new_group_id}", token=manage_groups_token)
    assert data["status"] == "success"
    assert data["data"]["name"] == group_name


def test_fetch_group_by_name(manage_groups_token, super_admin_user):
    group_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [super_admin_user.username]},
        token=manage_groups_token,
    )
    assert status == 200
    assert data["status"] == "success"
    new_group_id = data["data"]["id"]

    status, data = api("GET", f"groups?name={group_name}", token=manage_groups_token)
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == group_name
    assert data["data"][0]["id"] == new_group_id


def test_token_user_request_all_groups(manage_groups_token, super_admin_user):
    group_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [super_admin_user.username]},
        token=manage_groups_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", "groups", token=manage_groups_token)
    assert data["status"] == "success"
    assert data["data"]["user_groups"][-1]["name"] == group_name
    assert not any(
        [
            group["single_user_group"] is True
            and group["name"] == super_admin_user.username
            for group in data["data"]["user_groups"]
        ]
    )


def test_token_user_update_group(manage_groups_token, public_group):
    new_name = str(uuid.uuid4())
    status, data = api(
        "PUT",
        f"groups/{public_group.id}",
        data={"name": new_name},
        token=manage_groups_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"groups/{public_group.id}", token=manage_groups_token)
    assert data["status"] == "success"
    assert data["data"]["name"] == new_name


def test_token_user_delete_group(manage_groups_token, public_group):
    status, data = api("DELETE", f"groups/{public_group.id}", token=manage_groups_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"groups/{public_group.id}", token=manage_groups_token)
    assert status == 400


def test_manage_groups_token_get_unowned_group(
    manage_groups_token, user, super_admin_user
):
    group_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [user.username]},
        token=manage_groups_token,
    )
    assert status == 200
    assert data["status"] == "success"
    new_group_id = data["data"]["id"]

    token_name = str(uuid.uuid4())
    token_id = create_token(ACLs=['Manage groups'],
                            user_id=super_admin_user.id,
                            name=token_name)

    status, data = api("GET", f"groups/{new_group_id}", token=token_id)
    assert data["status"] == "success"
    assert data["data"]["name"] == group_name


def test_public_group(view_only_token):
    status, response = api(
        "GET",
        "groups/public",
        token=view_only_token
    )
    assert status == 200
    assert response["status"] == "success"
    int(response["data"]["id"])


def test_add_delete_stream_group(super_admin_token, public_group, public_stream):
    status, data = api(
        "POST",
        f"groups/{public_group.id}/streams",
        data={
            "stream_id": public_stream.id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["stream_id"] == public_stream.id

    status, data = api(
        "DELETE",
        f"groups/{public_group.id}/streams/{public_stream.id}",
        token=super_admin_token,
    )
    assert status == 200


def test_non_su_add_stream_to_group(manage_groups_token, public_group, public_stream):
    status, data = api(
        "POST",
        f"groups/{public_group.id}/streams",
        data={
            "stream_id": public_stream.id,
        },
        token=manage_groups_token,
    )
    assert status == 400


def test_add_already_added_stream_to_group(super_admin_token, public_group, public_stream):
    status, data = api(
        "POST",
        f"groups/{public_group.id}/streams",
        data={
            "stream_id": public_stream.id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["stream_id"] == public_stream.id

    status, data = api(
        "POST",
        f"groups/{public_group.id}/streams",
        data={
            "stream_id": public_stream.id,
        },
        token=super_admin_token,
    )
    assert status == 400
    assert data["message"] == "Specified stream is already associated with this group."
