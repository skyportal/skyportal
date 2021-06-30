import uuid
from skyportal.tests import api


def test_invite_new_user(manage_users_token, public_stream, public_group):
    status, _ = api(
        "POST",
        "invitations",
        data={
            "userEmail": "string",
            "streamIDs": [public_stream.id],
            "groupIDs": [public_group.id],
            "groupAdmin": [True],
        },
        token=manage_users_token,
    )
    assert status == 200


def test_invite_new_user_forbidden(view_only_token, public_stream, public_group):
    status, data = api(
        "POST",
        "invitations",
        data={
            "userEmail": "string",
            "streamIDs": [public_stream.id],
            "groupIDs": [public_group.id],
            "groupAdmin": [True],
        },
        token=view_only_token,
    )

    assert status == 400
    assert "Unauthorized" in data["message"]


def test_get_invitations(
    manage_users_token, manage_users_token_group2, public_stream, public_group
):
    status, data = api(
        "POST",
        "invitations",
        data={
            "userEmail": "string",
            "streamIDs": [public_stream.id],
            "groupIDs": [public_group.id],
            "groupAdmin": [True],
        },
        token=manage_users_token,
    )
    assert status == 200
    invitation_id = data["data"]["id"]

    # Whoever created the invitation can fetch it
    status, data = api(
        "GET",
        "invitations",
        params={"group": public_group.name},
        token=manage_users_token,
    )
    assert status == 200
    assert data["data"]["totalMatches"] == 1
    assert data["data"]["invitations"][0]["id"] == invitation_id

    # Only invitors can see the invitation
    status, data = api(
        "GET",
        "invitations",
        params={"group": public_group.name},
        token=manage_users_token_group2,
    )
    assert status == 200
    assert data["data"]["totalMatches"] == 0


def test_patch_invitation(
    manage_users_token,
    manage_users_token_group2,
    public_stream,
    public_group,
    public_group2,
):
    user_email = str(uuid.uuid4())
    status, data = api(
        "POST",
        "invitations",
        data={
            "userEmail": user_email,
            "streamIDs": [public_stream.id],
            "groupIDs": [public_group.id],
            "groupAdmin": [True],
        },
        token=manage_users_token,
    )
    assert status == 200
    invitation_id = data["data"]["id"]

    # Only the invitor should be able to patch
    status, data = api(
        "PATCH", f"invitations/{invitation_id}", token=manage_users_token_group2
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]

    # Need one of groupIDs or streamIDs
    status, data = api(
        "PATCH", f"invitations/{invitation_id}", token=manage_users_token
    )
    assert status == 400
    assert "At least one of" in data["message"]

    # Try adding group2 to the invited user
    status, _ = api(
        "PATCH",
        f"invitations/{invitation_id}",
        data={"groupIDs": [public_group2.id]},
        token=manage_users_token,
    )
    assert status == 200

    # Try updating role to View only
    status, _ = api(
        "PATCH",
        f"invitations/{invitation_id}",
        data={"role": "View only"},
        token=manage_users_token,
    )
    assert status == 200


def test_delete_invitation(
    manage_users_token,
    manage_users_token_group2,
    public_stream,
    public_group,
    public_group2,
):
    user_email = str(uuid.uuid4())
    status, data = api(
        "POST",
        "invitations",
        data={
            "userEmail": user_email,
            "streamIDs": [public_stream.id],
            "groupIDs": [public_group.id],
            "groupAdmin": [True],
        },
        token=manage_users_token,
    )
    assert status == 200
    invitation_id = data["data"]["id"]

    # Only the invitor should be able to delete
    status, data = api(
        "DELETE", f"invitations/{invitation_id}", token=manage_users_token_group2
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]

    # Try deleting invitation
    status, _ = api(
        "DELETE",
        f"invitations/{invitation_id}",
        token=manage_users_token,
    )
    assert status == 200
