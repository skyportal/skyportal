from skyportal.tests import api


def test_source_interest_lifecycle(
    upload_data_token, view_only_token, view_only_token2, public_source
):
    obj_id = public_source.id

    status, data = api(
        "POST",
        f"sources/{obj_id}/interests",
        data={
            "title": "Paper in preparation",
            "description": "photometric follow-up",
            "link": "https://example.com",
        },
        token=upload_data_token,
    )
    assert status == 200, data
    interest_id = data["data"]["id"]

    status, data = api("GET", f"sources/{obj_id}/interests", token=view_only_token)
    assert status == 200, data
    interests = data["data"]
    assert len(interests) == 1
    assert interests[0]["title"] == "Paper in preparation"
    assert interests[0]["link"] == "https://example.com"
    username = interests[0]["user"]["username"]
    assert username is not None

    status, data = api(
        "POST",
        f"sources/{obj_id}/interests",
        data={"title": "Second paper"},
        token=upload_data_token,
    )
    assert status == 200, data

    status, data = api("GET", f"sources/{obj_id}/interests", token=upload_data_token)
    assert status == 200, data
    assert [interest["title"] for interest in data["data"]] == [
        "Paper in preparation",
        "Second paper",
    ]
    assert data["data"][1]["description"] is None

    status, data = api(
        "DELETE", f"sources/{obj_id}/interests/{interest_id}", token=view_only_token2
    )
    assert status == 400, data

    status, data = api(
        "DELETE", f"sources/{obj_id}/interests/{interest_id}", token=upload_data_token
    )
    assert status == 200, data

    status, data = api("GET", f"sources/{obj_id}/interests", token=upload_data_token)
    assert status == 200, data
    assert [interest["title"] for interest in data["data"]] == ["Second paper"]

    status, data = api(
        "GET", f"sources/{obj_id}/comments?channel=Interested", token=view_only_token
    )
    assert status == 200, data
    messages = data["data"]
    assert all(
        message["channel"] == "Interested" and message["system"] is True
        for message in messages
    )
    assert sorted(message["text"] for message in messages) == sorted(
        [
            f"**{username}** registered an interest: **Paper in preparation**",
            f"**{username}** registered an interest: **Second paper**",
            f"**{username}** withdrew an interest: **Paper in preparation**",
        ]
    )


def test_conversations_stay_out_of_the_main_thread(
    comment_token, view_only_token, public_source
):
    obj_id = public_source.id

    for channel, text in [
        (None, "a regular comment"),
        ("Spectroscopy", "NOT time awarded"),
    ]:
        body = {"text": text}
        if channel:
            body["channel"] = channel
        status, data = api(
            "POST", f"sources/{obj_id}/comments", data=body, token=comment_token
        )
        assert status == 200, data

    status, data = api("GET", f"sources/{obj_id}/comments", token=view_only_token)
    assert status == 200, data
    texts = [c["text"] for c in data["data"]]
    assert "a regular comment" in texts
    assert "NOT time awarded" not in texts

    status, data = api(
        "GET", f"sources/{obj_id}/comments?channel=Spectroscopy", token=view_only_token
    )
    assert status == 200, data
    assert [c["text"] for c in data["data"]] == ["NOT time awarded"]

    status, data = api(
        "GET", f"sources/{obj_id}/comments/channels", token=view_only_token
    )
    assert status == 200, data
    assert data["data"] == ["Spectroscopy"]

    status, data = api(
        "GET", f"sources/{obj_id}?includeComments=true", token=view_only_token
    )
    assert status == 200, data
    texts = [c["text"] for c in data["data"]["comments"]]
    assert "a regular comment" in texts
    assert "NOT time awarded" not in texts


def test_conversation_deletion_permissions(
    comment_token, view_only_token, view_only_token2, super_admin_token, public_source
):
    obj_id = public_source.id

    status, data = api(
        "POST",
        f"sources/{obj_id}/comments",
        data={"text": "opening", "channel": "Photometry"},
        token=comment_token,
    )
    assert status == 200, data

    status, data = api(
        "DELETE",
        f"sources/{obj_id}/comments/channels?channel=Photometry",
        token=view_only_token2,
    )
    assert status == 403, data

    status, data = api(
        "DELETE",
        f"sources/{obj_id}/comments/channels?channel=Photometry",
        token=super_admin_token,
    )
    assert status == 200, data

    status, data = api(
        "GET", f"sources/{obj_id}/comments/channels", token=view_only_token
    )
    assert status == 200, data
    assert data["data"] == []

    status, data = api(
        "DELETE",
        f"sources/{obj_id}/comments/channels?channel=Unknown",
        token=view_only_token,
    )
    assert status == 400, data
