from skyportal.tests import api, assert_api, assert_api_fail


def test_group_admission_existing_member(user, public_group, upload_data_token):
    request_data = {"groupID": public_group.id, "userID": user.id}

    status, data = api(
        "POST", "group_admission_requests", data=request_data, token=upload_data_token
    )
    assert_api_fail(status, data, 400, "already a member of group")


def test_group_admission_read_access(
    public_group,
    user_group2,
    upload_data_token,
    upload_data_token_group2,
    manage_sources_token,
    view_only_token,
):
    # Have user_group2 request access to public_group
    request_data = {"groupID": public_group.id, "userID": user_group2.id}

    status, data = api(
        "POST",
        "group_admission_requests",
        data=request_data,
        token=upload_data_token_group2,
    )
    assert_api(status, data)
    request_id = data["data"]["id"]

    # user_group2 can read their own request
    status, data = api(
        "GET",
        f"group_admission_requests/{request_id}",
        token=upload_data_token_group2,
    )
    assert_api(status, data)

    # group_admin_user is associated with the manages_sources_token and
    # should be able to see the request just submitted
    status, data = api(
        "GET",
        f"group_admission_requests/{request_id}",
        token=manage_sources_token,
    )
    assert_api(status, data)

    # Regular user (upload_data_token) should not be able to see the request
    # as they are neither a group admin nor the requesting user
    status, data = api(
        "GET",
        f"group_admission_requests/{request_id}",
        token=view_only_token,
    )
    assert_api_fail(
        status, data, 400, "User must be group admin or requester to see request"
    )


# test get doesn't exist
def test_group_admission_read_nonexistent(upload_data_token):
    request_id = 9999999
    status, data = api(
        "GET",
        f"group_admission_requests/{request_id}",
        token=upload_data_token,
    )
    assert status == 400
    assert "Could not find an admission request with the ID" in data["message"]


# test post for someone not me
def test_group_admission_post_for_another_user(
    user_group2, public_group, upload_data_token
):
    request_data = {"groupID": public_group.id, "userID": user_group2.id}

    status, data = api(
        "POST", "group_admission_requests", data=request_data, token=upload_data_token
    )
    assert status == 400
    assert "cannot be made on behalf of others" in data["message"]


# test patch non-admin
def test_group_admission_patch_permissions(
    public_group,
    user_group2,
    upload_data_token,
    upload_data_token_group2,
    group_admin_token,
):
    # Have user_group2 request access to public_group
    request_data = {"groupID": public_group.id, "userID": user_group2.id}

    status, data = api(
        "POST",
        "group_admission_requests",
        data=request_data,
        token=upload_data_token_group2,
    )
    assert status == 200
    assert data["status"] == "success"
    request_id = data["data"]["id"]

    # Regular user is not a group admin and cannot approve the request
    status, data = api(
        "PATCH",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=upload_data_token,
    )
    assert status == 400
    assert "Insufficient permissions for operation" in data["message"]

    # Nor can the requesting user do so
    status, data = api(
        "PATCH",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=upload_data_token_group2,
    )
    assert status == 400
    assert (
        "Insufficient permissions: group admission request status can only be changed by group admins."
        in data["message"]
    )

    # The group admin can approve the request
    status, data = api(
        "PATCH",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=group_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"


# test delete someone else
def test_group_admission_delete_permissions(
    public_group,
    user_group2,
    upload_data_token,
    upload_data_token_group2,
    group_admin_token,
):
    # Have user_group2 request access to public_group
    request_data = {"groupID": public_group.id, "userID": user_group2.id}

    status, data = api(
        "POST",
        "group_admission_requests",
        data=request_data,
        token=upload_data_token_group2,
    )
    assert status == 200
    assert data["status"] == "success"
    request_id = data["data"]["id"]

    # Regular user cannot delete the request
    status, data = api(
        "DELETE",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=upload_data_token,
    )
    assert status == 400
    assert (
        "Insufficient permissions: only the requester can delete a group admission request."
        in data["message"]
    )

    # Nor can the group admin do so
    status, data = api(
        "DELETE",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=group_admin_token,
    )
    assert status == 400
    assert (
        "Insufficient permissions: only the requester can delete a group admission request."
        in data["message"]
    )

    # The requester can approve the request
    status, data = api(
        "DELETE",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=upload_data_token_group2,
    )
    assert status == 200
    assert data["status"] == "success"
