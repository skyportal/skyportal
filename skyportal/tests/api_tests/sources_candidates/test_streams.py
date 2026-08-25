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
        data={"name": new_name},
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


def test_super_admin_grant_delete_user_stream_access(
    super_admin_token, user, public_stream2
):
    status, data = api(
        "POST",
        f"streams/{public_stream2.id}/users",
        data={"user_id": user.id},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "DELETE",
        f"streams/{public_stream2.id}/users/{user.id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"


def test_group_admin_cannot_grant_delete_user_stream_access(
    group_admin_token, user, public_stream, public_stream2
):
    # Non-admins cannot grant access to other users (public_stream2 is not
    # auto-join), so the handler rejects the request.
    status, data = api(
        "POST",
        f"streams/{public_stream2.id}/users",
        data={"user_id": user.id},
        token=group_admin_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]

    status, data = api(
        "DELETE", f"streams/{public_stream.id}/users/{user.id}", token=group_admin_token
    )
    assert status == 401


def test_user_cannot_grant_self_stream_access(view_only_token, user, public_stream2):
    # public_stream2 is not auto-join, so a user cannot add themselves.
    status, data = api(
        "POST",
        f"streams/{public_stream2.id}/users",
        data={"user_id": user.id},
        token=view_only_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]


def test_auto_join_stream_visible_to_non_member(
    super_admin_token, view_only_token, user, public_stream2
):
    # public_stream2 is not one of the user's streams and is not auto-join, so
    # the user cannot see it...
    status, data = api("GET", f"streams/{public_stream2.id}", token=view_only_token)
    assert status == 400
    assert "Could not retrieve stream" in data["message"]

    status, listing = api("GET", "streams", token=view_only_token)
    assert status == 200
    assert public_stream2.id not in [s["id"] for s in listing["data"]]

    # ...but once flagged auto-join it becomes visible (for discovery/joining),
    # even though the user is not yet a member.
    status, data = api(
        "PATCH",
        f"streams/{public_stream2.id}",
        data={"name": public_stream2.name, "auto_join": True},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"streams/{public_stream2.id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == public_stream2.id
    assert data["data"]["auto_join"] is True

    status, listing = api("GET", "streams", token=view_only_token)
    assert status == 200
    assert public_stream2.id in [s["id"] for s in listing["data"]]


def test_user_can_self_join_auto_join_stream(
    super_admin_token, view_only_token, user, public_stream2
):
    # Flag the stream as auto-join
    status, data = api(
        "PATCH",
        f"streams/{public_stream2.id}",
        data={"name": public_stream2.name, "auto_join": True},
        token=super_admin_token,
    )
    assert status == 200

    # The user can now add themselves
    status, data = api(
        "POST",
        f"streams/{public_stream2.id}/users",
        data={"user_id": user.id},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # ...and the stream is now readable by (accessible to) the user
    status, data = api("GET", f"streams/{public_stream2.id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == public_stream2.id

    # ...and shows up among the user's own streams in their profile
    status, data = api("GET", "internal/profile", token=view_only_token)
    assert status == 200
    assert public_stream2.id in [s["id"] for s in data["data"]["streams"]]


def test_user_cannot_add_other_user_to_auto_join_stream(
    super_admin_token, view_only_token, user2, public_stream2
):
    # Even on an auto-join stream, a non-admin may add only themselves.
    status, data = api(
        "PATCH",
        f"streams/{public_stream2.id}",
        data={"name": public_stream2.name, "auto_join": True},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        f"streams/{public_stream2.id}/users",
        data={"user_id": user2.id},
        token=view_only_token,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]
