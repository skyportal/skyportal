import uuid
from skyportal.tests import api


def test_token_user_post_new_stream(super_admin_token, public_stream):
    status, data = api(
        "POST",
        "streams",
        data={
            "name": str(uuid.uuid4()),
            "altdata": {"collection": "ZTF_alerts", "selector": [1, 2, 3]},
        },
        token=super_admin_token,
    )
    assert status == 200
    stream_id = data["data"]["id"]

    status, data = api("GET", f"streams/{stream_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["id"] == stream_id


def test_token_user_update_stream(super_admin_token, public_stream):
    new_name = str(uuid.uuid4())
    status, data = api(
        "PATCH",
        f"streams/{public_stream.id}",
        data={
            "name": new_name,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"streams/{public_stream.id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["name"] == new_name


def test_token_user_delete_stream(super_admin_token, public_stream):
    status, data = api(
        "POST",
        "streams",
        data={
            "name": str(uuid.uuid4()),
            "altdata": {"collection": "ZTF_alerts", "selector": [1, 2, 3]},
        },
        token=super_admin_token,
    )
    assert status == 200
    stream_id = data["data"]["id"]

    status, data = api("DELETE", f"streams/{stream_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
