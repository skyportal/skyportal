from skyportal.tests import api


def test_feedback(view_only_token, view_only_token2, super_admin_token):
    status, data = api(
        "POST",
        "feedback",
        data={"category": "bug", "text": "The button is broken"},
        token=view_only_token,
    )
    assert status == 200
    feedback_id = data["data"]["id"]

    status, data = api("GET", "feedback", token=view_only_token)
    assert status == 200
    assert feedback_id in [m["id"] for m in data["data"]["messages"]]

    status, data = api("GET", "feedback", token=view_only_token2)
    assert status == 200
    assert feedback_id not in [m["id"] for m in data["data"]["messages"]]

    status, _ = api(
        "PATCH",
        f"feedback/{feedback_id}",
        data={"resolved": True},
        token=view_only_token,
    )
    assert status == 403

    status, _ = api(
        "PATCH",
        f"feedback/{feedback_id}",
        data={"resolved": True},
        token=super_admin_token,
    )
    assert status == 200
    status, data = api("GET", f"feedback/{feedback_id}", token=super_admin_token)
    assert data["data"]["messages"][0]["resolved"]


def test_feedback_replies(view_only_token, super_admin_token):
    status, data = api(
        "POST",
        "feedback",
        data={"category": "change", "text": "Please add a dark mode"},
        token=view_only_token,
    )
    assert status == 200
    feedback_id = data["data"]["id"]

    status, _ = api(
        "POST",
        f"feedback/{feedback_id}/replies",
        data={"text": "I can reply to myself"},
        token=view_only_token,
    )
    assert status == 403

    status, _ = api(
        "POST",
        f"feedback/{feedback_id}/replies",
        data={"text": "It already exists, in your profile"},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"feedback/{feedback_id}", token=view_only_token)
    assert status == 200
    replies = data["data"]["messages"][0]["replies"]
    assert [r["text"] for r in replies] == ["It already exists, in your profile"]


def test_feedback_rejects_unknown_category(view_only_token):
    status, _ = api(
        "POST",
        "feedback",
        data={"category": "praise", "text": "Nice"},
        token=view_only_token,
    )
    assert status == 400
