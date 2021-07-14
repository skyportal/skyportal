import uuid
from skyportal.tests import api
from skyportal.model_util import create_token
from baselayer.app.env import load_env

_, cfg = load_env()


def test_token_user_create_new_group(super_admin_token, super_admin_user):
    group_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [super_admin_user.id]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    new_group_id = data["data"]["id"]

    status, data = api("GET", f"groups/{new_group_id}", token=super_admin_token)
    assert data["status"] == "success"
    assert data["data"]["name"] == group_name


def test_cannot_create_group_empty_string_name(manage_groups_token, super_admin_user):
    group_name = ""
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [super_admin_user.id]},
        token=manage_groups_token,
    )
    assert status == 400
    assert "Missing required parameter" in data["message"]


def test_fetch_group_by_name(super_admin_token, super_admin_user):
    group_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [super_admin_user.id]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    new_group_id = data["data"]["id"]

    status, data = api("GET", f"groups?name={group_name}", token=super_admin_token)
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == group_name
    assert data["data"][0]["id"] == new_group_id


def test_fetch_group_exclude_users(super_admin_token, public_group):
    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=False",
        token=super_admin_token,
    )
    assert data["status"] == "success"
    assert "users" not in data["data"]


def test_token_user_request_all_groups(super_admin_token, super_admin_user):
    group_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [super_admin_user.id]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", "groups", token=super_admin_token)
    assert data["status"] == "success"
    assert any(
        [user_group["name"] == group_name for user_group in data["data"]["user_groups"]]
    )
    assert any(
        [
            group["single_user_group"] is True
            and group["name"] == super_admin_user.username
            for group in data["data"]["user_groups"]
        ]
    )
    assert any(
        [
            user_group["name"] == group_name
            for user_group in data["data"]["user_accessible_groups"]
        ]
    )
    assert not any(
        [
            group["single_user_group"] is True
            and group["name"] == super_admin_user.username
            for group in data["data"]["user_accessible_groups"]
        ]
    )


def test_token_user_update_group(super_admin_token, public_group):
    new_name = str(uuid.uuid4())
    status, data = api(
        "PUT",
        f"groups/{public_group.id}",
        data={"name": new_name},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"groups/{public_group.id}", token=super_admin_token)
    assert data["status"] == "success"
    assert data["data"]["name"] == new_name


def test_token_user_delete_group(super_admin_token, public_group):
    status, data = api("DELETE", f"groups/{public_group.id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"groups/{public_group.id}", token=super_admin_token)
    assert status == 400


def test_manage_groups_token_get_unowned_group(
    super_admin_token, user, super_admin_user
):
    group_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "groups",
        data={"name": group_name, "group_admins": [user.id]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    new_group_id = data["data"]["id"]

    token_name = str(uuid.uuid4())
    token_id = create_token(
        ACLs=['Manage groups'], user_id=super_admin_user.id, name=token_name
    )

    status, data = api("GET", f"groups/{new_group_id}", token=token_id)
    assert data["status"] == "success"
    assert data["data"]["name"] == group_name


def test_public_group(view_only_token):
    status, response = api("GET", "groups/public", token=view_only_token)
    assert status == 200
    assert response["status"] == "success"
    int(response["data"]["id"])


def test_add_delete_stream_group(
    super_admin_token, public_group_no_streams, public_stream
):
    status, data = api(
        "POST",
        f"groups/{public_group_no_streams.id}/streams",
        data={"stream_id": public_stream.id},
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["stream_id"] == public_stream.id

    status, data = api(
        "DELETE",
        f"groups/{public_group_no_streams.id}/streams/{public_stream.id}",
        token=super_admin_token,
    )
    assert status == 200


def test_non_su_add_stream_to_group(
    manage_groups_token, public_group_no_streams, public_stream
):
    status, data = api(
        "POST",
        f"groups/{public_group_no_streams.id}/streams",
        data={"stream_id": public_stream.id},
        token=manage_groups_token,
    )
    assert status == 400


def test_add_already_added_stream_to_group(
    super_admin_token, public_group_no_streams, public_stream
):
    status, data = api(
        "POST",
        f"groups/{public_group_no_streams.id}/streams",
        data={"stream_id": public_stream.id},
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["stream_id"] == public_stream.id

    status, data = api(
        "POST",
        f"groups/{public_group_no_streams.id}/streams",
        data={"stream_id": public_stream.id},
        token=super_admin_token,
    )
    assert status == 400
    assert data["message"] == "Specified stream is already associated with this group."


def test_add_stream_to_single_user_group_delete_stream(
    super_admin_token, super_admin_user, public_group_no_streams, public_stream
):
    # create new user
    username = str(uuid.uuid4())
    status, data = api(
        "POST", "user", data={"username": username}, token=super_admin_token
    )
    assert status == 200

    # get single-user group
    status, data = api(
        "GET", "groups?includeSingleUserGroups=true", token=super_admin_token
    )
    assert data["status"] == "success"
    assert any(
        [
            group["single_user_group"] and group["name"] == username
            for group in data["data"]["all_groups"]
        ]
    )
    single_user_group = [
        group for group in data["data"]["all_groups"] if group["name"] == username
    ][0]

    # add stream to this group
    status, data = api(
        "POST",
        f"groups/{single_user_group['id']}/streams",
        data={"stream_id": public_stream.id},
        token=super_admin_token,
    )

    # check that you can't add a stream to a single user group
    assert status == 400
    assert data['status'] == 'error'


def test_add_stream_to_group_delete_stream(
    super_admin_token, public_group_no_streams, public_stream
):
    status, data = api(
        "POST",
        f"groups/{public_group_no_streams.id}/streams",
        data={"stream_id": public_stream.id},
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["stream_id"] == public_stream.id

    # check stream is there
    status, data = api(
        "GET",
        f"groups/{public_group_no_streams.id}",
        token=super_admin_token,
    )
    assert data["data"]["streams"][0]["id"] == public_stream.id

    # delete stream
    status, data = api(
        "DELETE",
        f"streams/{public_stream.id}",
        token=super_admin_token,
    )
    assert status == 200

    # check group still exists and stream is not there
    status, data = api(
        "GET",
        f"groups/{public_group_no_streams.id}",
        token=super_admin_token,
    )
    assert len(data["data"]["streams"]) == 0


def test_post_new_filter_delete_group_deletes_filter(
    super_admin_token, group_with_stream, public_stream
):
    status, data = api(
        "POST",
        "filters",
        data={
            "name": str(uuid.uuid4()),
            "stream_id": public_stream.id,
            "group_id": group_with_stream.id,
        },
        token=super_admin_token,
    )
    assert status == 200
    filter_id = data["data"]["id"]

    status, data = api("GET", f"filters/{filter_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["id"] == filter_id

    status, data = api(
        "DELETE", f"groups/{group_with_stream.id}", token=super_admin_token
    )
    assert status == 200

    status, data = api("GET", f"filters/{filter_id}", token=super_admin_token)
    assert status == 400
    assert "Invalid Filter id" in data["message"]


def test_post_new_filter_delete_stream_deletes_filter(
    super_admin_token, group_with_stream, public_stream
):
    status, data = api(
        "POST",
        "filters",
        data={
            "name": str(uuid.uuid4()),
            "stream_id": public_stream.id,
            "group_id": group_with_stream.id,
        },
        token=super_admin_token,
    )
    assert status == 200
    filter_id = data["data"]["id"]

    status, data = api("GET", f"filters/{filter_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["id"] == filter_id

    status, data = api("DELETE", f"streams/{public_stream.id}", token=super_admin_token)
    assert status == 200

    status, data = api("GET", f"filters/{filter_id}", token=super_admin_token)
    assert status == 400
    assert "Invalid Filter id" in data["message"]


def test_cannot_delete_sitewide_public_group(super_admin_token):
    status, data = api(
        "GET", f"groups?name={cfg['misc.public_group_name']}", token=super_admin_token
    )
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == cfg['misc.public_group_name']
    group_id = data["data"][0]["id"]

    status, data = api("DELETE", f"groups/{group_id}", token=super_admin_token)
    assert data["status"] == "error"
    assert "Insufficient permissions" in data["message"]


def test_obj_groups(public_source, public_group, super_admin_token):
    status, data = api(
        'GET', f'sources/{public_source.id}/groups', token=super_admin_token
    )
    assert status == 200
    assert data["data"][0]["id"] == public_group.id


def test_add_user_to_group(public_group, user_group2, super_admin_token):
    status, data = api(
        "POST",
        f"groups/{public_group.id}/users",
        data={"userID": user_group2.id, "admin": False, "canSave": False},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=true",
        token=super_admin_token,
    )
    group_user = None
    for gu in data["data"]["users"]:
        if gu["id"] == user_group2.id:
            group_user = gu
    assert group_user is not None
    assert not group_user["can_save"]
    assert not group_user["admin"]


def test_cannot_add_user_to_group_wout_stream_access(
    public_group_stream2, super_admin_token, user
):
    status, data = api(
        "POST",
        f"groups/{public_group_stream2.id}/users",
        data={"userID": user.id, "admin": False},
        token=super_admin_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]


def test_cannot_delete_stream_actively_filtered(
    public_group, public_stream, public_filter, super_admin_token
):
    status, data = api(
        "DELETE",
        f"groups/{public_group.id}/streams/{public_stream.id}",
        token=super_admin_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]


def test_delete_stream_not_actively_filtered(
    public_group_two_streams,
    public_group,
    public_stream,
    public_stream2,
    public_filter,
    super_admin_token,
):
    status, data = api(
        "DELETE",
        f"groups/{public_group.id}/streams/{public_stream.id}",
        token=super_admin_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]

    status, data = api(
        "DELETE",
        f"groups/{public_group_two_streams.id}/streams/{public_stream2.id}",
        token=super_admin_token,
    )
    assert status == 200


def test_update_group_user_admin_status(public_group, group_admin_token, user):
    status, data = api(
        "PATCH",
        f"groups/{public_group.id}/users",
        data={"userID": user.id, "admin": True},
        token=group_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=true",
        token=group_admin_token,
    )
    group_user = None
    for gu in data["data"]["users"]:
        if gu["id"] == user.id:
            group_user = gu
    assert group_user is not None
    assert group_user["admin"]
    assert group_user["can_save"]


def test_update_group_user_save_access_status(public_group, group_admin_token, user):
    status, data = api(
        "PATCH",
        f"groups/{public_group.id}/users",
        data={"userID": user.id, "canSave": False},
        token=group_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=true",
        token=group_admin_token,
    )
    group_user = None
    for gu in data["data"]["users"]:
        if gu["id"] == user.id:
            group_user = gu
    assert group_user is not None
    assert not group_user["can_save"]


def test_non_group_admin_cannot_update_group_user_admin_status(
    public_group, manage_users_token, user
):
    status, data = api(
        "PATCH",
        f"groups/{public_group.id}/users",
        data={"userID": user.id, "admin": True},
        token=manage_users_token,
    )
    assert status == 400


def test_remove_self_from_group(public_group, view_only_token, user):
    status, data = api(
        "DELETE",
        f"groups/{public_group.id}/users/{user.id}",
        token=view_only_token,
    )
    assert status == 200


def test_super_admin_remove_user_from_group(public_group, super_admin_token, user):
    status, data = api(
        "DELETE",
        f"groups/{public_group.id}/users/{user.id}",
        token=super_admin_token,
    )
    assert status == 200


def test_group_admin_remove_user_from_group(public_group, group_admin_token, user):
    status, data = api(
        "DELETE",
        f"groups/{public_group.id}/users/{user.id}",
        token=group_admin_token,
    )
    assert status == 200


def test_non_group_admin_cannot_remove_user_from_group(
    public_group, view_only_token2, user
):
    status, data = api(
        "DELETE",
        f"groups/{public_group.id}/users/{user.id}",
        token=view_only_token2,
    )
    assert status == 400


def test_cannot_add_self_to_group(public_group2, view_only_token, user):
    status, data = api(
        "POST",
        f"groups/{public_group2.id}/users",
        data={"userID": user.id, "admin": False},
        token=view_only_token,
    )
    assert status == 400
    assert "Unauthorized" in data["message"]


def test_super_admin_add_user_to_group(public_group2, super_admin_token, user):
    status, data = api(
        "POST",
        f"groups/{public_group2.id}/users",
        data={"userID": user.id, "admin": False},
        token=super_admin_token,
    )
    assert status == 200


def test_group_admin_add_user_to_group(public_group, group_admin_token, user_group2):
    status, data = api(
        "POST",
        f"groups/{public_group.id}/users",
        data={"userID": user_group2.id, "admin": False, "canSave": True},
        token=group_admin_token,
    )
    assert status == 200


def test_non_group_admin_cannot_add_user_to_group(
    public_group2, group_admin_token, user
):
    status, data = api(
        "POST",
        f"groups/{public_group2.id}/users",
        data={"userID": user.id, "admin": False},
        token=group_admin_token,
    )
    assert status == 400
    assert "Insufficient permission" in data["message"]


def test_cannot_add_stream_to_single_user_group(super_admin_token, user, public_stream):
    single_user_group = user.single_user_group
    assert single_user_group is not None
    status, data = api(
        "POST",
        f"groups/{single_user_group.id}/streams",
        data={"stream_id": public_stream.id},
        token=super_admin_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]


def test_cannot_add_another_user_to_single_user_group(user2, super_admin_token, user):
    single_user_group = user2.single_user_group
    assert single_user_group is not None
    status, data = api(
        "POST",
        f"groups/{single_user_group.id}/users",
        data={"userID": user.id, "admin": False},
        token=super_admin_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]


def test_cannot_remove_user_from_single_user_group(super_admin_token, user):
    single_user_group = user.single_user_group
    assert single_user_group is not None
    status, data = api(
        "DELETE",
        f"groups/{single_user_group.id}/users/{user.id}",
        token=super_admin_token,
    )
    assert status == 400


def test_user_cannot_remove_self_from_single_user_group(view_only_token, user):
    single_user_group = user.single_user_group
    assert single_user_group is not None
    status, data = api(
        "DELETE",
        f"groups/{single_user_group.id}/users/{user.id}",
        token=view_only_token,
    )
    assert status == 400
