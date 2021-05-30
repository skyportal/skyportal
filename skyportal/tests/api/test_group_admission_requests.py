from skyportal.tests import api


def test_group_admission_existing_member(user, public_group, upload_data_token):
    request_data = {'groupID': public_group.id, 'userID': user.id}

    status, data = api(
        'POST', 'group_admission_requests', data=request_data, token=upload_data_token
    )
    assert status == 400
    assert "already a member of group" in data["message"]


def test_group_admission_read_access(
    public_group,
    user_group2,
    upload_data_token,
    upload_data_token_group2,
    manage_sources_token,
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

    # user_group2 can read their own request
    status, data = api(
        "GET",
        f"group_admission_requests/{request_id}",
        token=upload_data_token_group2,
    )
    assert status == 200
    assert data["status"] == "success"

    # group_admin_user is associated with the manages_sources_token and
    # should be able to see the request just submitted
    status, data = api(
        "GET",
        f"group_admission_requests/{request_id}",
        token=manage_sources_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # Regular user (upload_data_token) should not be able to see the request
    # as they are neither a group admin nor the requesting user
    status, data = api(
        "GET",
        f"group_admission_requests/{request_id}",
        token=upload_data_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]


# test get doesn't exist
def test_group_admission_read_nonexistent(upload_data_token):
    request_id = 9999999
    status, data = api(
        "GET",
        f"group_admission_requests/{request_id}",
        token=upload_data_token,
    )
    assert status == 400
    assert "Invalid GroupAdmissionRequest id" in data["message"]


# test post for someone not me
def test_group_admission_post_for_another_user(
    user_group2, public_group, upload_data_token
):
    request_data = {'groupID': public_group.id, 'userID': user_group2.id}

    status, data = api(
        'POST', 'group_admission_requests', data=request_data, token=upload_data_token
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]


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
    assert "Insufficient permissions" in data["message"]

    # Nor can the requesting user do so
    status, data = api(
        "PATCH",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=upload_data_token_group2,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]

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
    assert "Insufficient permissions" in data["message"]

    # Nor can the group admin do so
    status, data = api(
        "DELETE",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=group_admin_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]

    # The requester can approve the request
    status, data = api(
        "DELETE",
        f"group_admission_requests/{request_id}",
        data={"status": "accepted"},
        token=upload_data_token_group2,
    )
    assert status == 200
    assert data["status"] == "success"
