import uuid

from skyportal.tests import api


def test_filter_list(view_only_token, public_filter):
    status, data = api("GET", "filters", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"][0] for k in ["name", "group_id", "stream_id"])


def test_token_user_retrieving_filter(view_only_token, public_filter):
    status, data = api("GET", f"filters/{public_filter.id}", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"] for k in ["name", "group_id", "stream_id"])


def test_token_user_update_filter(manage_groups_token, public_filter):
    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={"name": "new_name"},
        token=manage_groups_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"filters/{public_filter.id}", token=manage_groups_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["name"] == "new_name"


def test_cannot_update_filter_group_stream(view_only_token, public_filter):
    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={"group_id": 0},
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"

    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={"stream_id": 0},
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"


def test_token_user_post_delete_filter(
    manage_groups_token, group_with_stream, public_stream
):
    status, data = api(
        "POST",
        "filters",
        data={
            "name": str(uuid.uuid4()),
            "stream_id": public_stream.id,
            "group_id": group_with_stream.id,
        },
        token=manage_groups_token,
    )
    assert status == 200
    filter_id = data["data"]["id"]

    status, data = api("GET", f"filters/{filter_id}", token=manage_groups_token)
    assert status == 200
    assert data["data"]["id"] == filter_id

    status, data = api("DELETE", f"filters/{filter_id}", token=manage_groups_token)
    assert status == 200

    status, data = api("GET", f"filters/{filter_id}", token=manage_groups_token)
    assert status == 400
    assert "Cannot find a filter with ID" in data["message"]


def test_post_filter_with_unauthorized_stream(
    manage_groups_token, group_with_stream, public_stream
):
    status, data = api(
        "POST",
        "filters",
        data={
            "name": str(uuid.uuid4()),
            "stream_id": public_stream.id - 1,
            "group_id": group_with_stream.id,
        },
        token=manage_groups_token,
    )
    assert status in [401, 500]
