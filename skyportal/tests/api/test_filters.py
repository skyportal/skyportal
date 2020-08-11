import uuid
from skyportal.tests import api


def test_filter_list(view_only_token, public_filter):
    status, data = api("GET", "filters", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert all(
        k in data["data"][0]
        for k in ["query_string", "group_id"]
    )


def test_token_user_retrieving_filter(view_only_token, public_filter):
    status, data = api(
        "GET", f"filters/{public_filter.id}", token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(
        k in data["data"]
        for k in ["query_string", "group_id"]
    )


def test_token_user_update_filter(manage_groups_token, public_filter):
    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={
            "query_string": "new_qstr"
        },
        token=manage_groups_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"filters/{public_filter.id}", token=manage_groups_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["query_string"] == "new_qstr"


def test_cannot_update_filter_without_permission(view_only_token, public_filter):
    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={
            "query_string": "new_qstr"
        },
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_token_user_post_new_filter(manage_groups_token, public_group):
    status, data = api(
        "POST",
        "filters",
        data={
            "query_string": str(uuid.uuid4()),
            "group_id": public_group.id,
        },
        token=manage_groups_token,
    )
    assert status == 200
    filter_id = data["data"]["id"]

    status, data = api("GET", f"filters/{filter_id}", token=manage_groups_token)
    assert status == 200
    assert data["data"]["id"] == filter_id
