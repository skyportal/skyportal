"""Admin access to another user's profile and notification preferences."""

from skyportal.tests import api


def test_admin_sets_another_users_notification_preferences(
    super_admin_token, view_only_token, user
):
    """An admin turns a notification on, and the user sees it on their own profile."""
    status, data = api(
        "PATCH",
        f"internal/profile/{user.id}",
        data={"preferences": {"notifications": {"gcn_matches": {"active": True}}}},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", "internal/profile", token=view_only_token)
    assert status == 200
    assert data["data"]["preferences"]["notifications"]["gcn_matches"]["active"] is True


def test_admin_reads_another_users_preferences(super_admin_token, user):
    status, data = api(
        "PATCH",
        f"internal/profile/{user.id}",
        data={"preferences": {"notifications": {"gcn_matches": {"active": True}}}},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"internal/profile/{user.id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["id"] == user.id
    assert data["data"]["preferences"]["notifications"]["gcn_matches"]["active"] is True


def test_another_users_profile_carries_no_tokens(
    super_admin_token, view_only_token, user
):
    """A token id is the bearer secret, so only the owner's own read lists them."""
    status, data = api("GET", "internal/profile", token=view_only_token)
    assert status == 200
    assert [token["id"] for token in data["data"]["tokens"]] == [view_only_token]

    status, data = api("GET", f"internal/profile/{user.id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["tokens"] == []


def test_a_non_admin_cannot_read_another_users_profile(view_only_token, user2):
    _, data = api("GET", f"internal/profile/{user2.id}", token=view_only_token)
    assert data["status"] == "error"
    assert f"Cannot find User with ID: {user2.id}" in data["message"]


def test_a_non_admin_cannot_write_another_users_preferences(
    view_only_token, super_admin_token, user2
):
    _, data = api(
        "PATCH",
        f"internal/profile/{user2.id}",
        data={"preferences": {"notifications": {"gcn_matches": {"active": True}}}},
        token=view_only_token,
    )
    assert data["status"] == "error"

    status, data = api("GET", f"internal/profile/{user2.id}", token=super_admin_token)
    assert status == 200
    notifications = data["data"]["preferences"].get("notifications") or {}
    assert "gcn_matches" not in notifications


def test_a_non_admin_still_reads_and_writes_their_own_profile(view_only_token, user):
    status, data = api(
        "PATCH",
        f"internal/profile/{user.id}",
        data={"preferences": {"notifications": {"gcn_matches": {"active": True}}}},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"internal/profile/{user.id}", token=view_only_token)
    assert status == 200
    assert data["data"]["tokens"], "own profile keeps its tokens when named by id"


def test_preferences_are_merged_rather_than_replaced(super_admin_token, user):
    """The narrowing lists save separately from the switch that activates them."""
    status, _ = api(
        "PATCH",
        f"internal/profile/{user.id}",
        data={"preferences": {"notifications": {"gcn_matches": {"active": True}}}},
        token=super_admin_token,
    )
    assert status == 200

    status, _ = api(
        "PATCH",
        f"internal/profile/{user.id}",
        data={"preferences": {"notifications": {"gcn_matches": {"gcn_tags": ["GRB"]}}}},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"internal/profile/{user.id}", token=super_admin_token)
    assert status == 200
    gcn_matches = data["data"]["preferences"]["notifications"]["gcn_matches"]
    assert gcn_matches["active"] is True
    assert gcn_matches["gcn_tags"] == ["GRB"]


def test_gcn_event_properties_reach_a_user_with_no_notifications(
    super_admin_token, user
):
    """The properties list is replaced wholesale, so it must not assume a parent."""
    status, _ = api(
        "PATCH",
        f"internal/profile/{user.id}",
        data={"preferences": {"theme": "dark"}},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "PATCH",
        f"internal/profile/{user.id}",
        data={
            "preferences": {
                "notifications": {"gcn_events": {"properties": [{"far": 1}]}}
            }
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"internal/profile/{user.id}", token=super_admin_token)
    assert status == 200
    properties = data["data"]["preferences"]["notifications"]["gcn_events"][
        "properties"
    ]
    assert properties == [{"far": 1}]
