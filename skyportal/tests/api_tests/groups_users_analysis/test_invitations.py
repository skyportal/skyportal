import uuid

from skyportal.tests import api


def test_invite_new_user(manage_users_token, public_stream, public_group):
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
    print(status)
    print(data)
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

    assert status == 401
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
    print(status)
    print(data)
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
    print(status)
    print(data)
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
    print(status)
    print(data)
    assert status == 200
    invitation_id = data["data"]["id"]

    # Only the invitor should be able to delete
    status, data = api(
        "DELETE", f"invitations/{invitation_id}", token=manage_users_token_group2
    )
    print("-------")
    print(status)
    print(data)
    assert status == 400
    assert "Insufficient permissions" in data["message"]

    # Try deleting invitation
    status, _ = api(
        "DELETE",
        f"invitations/{invitation_id}",
        token=manage_users_token,
    )
    assert status == 200


def invitation_arrays(invitation_id, token):
    """The per-group flag arrays alongside the groups they are positional against."""
    status, data = api("GET", "invitations", token=token)
    assert status == 200
    invitation = next(
        i for i in data["data"]["invitations"] if i["id"] == invitation_id
    )
    return (
        [g["id"] for g in invitation["groups"]],
        invitation["admin_for_groups"],
        invitation["can_save_to_groups"],
        invitation["can_share_photometry_for_groups"],
    )


def test_patch_invitation_keeps_flag_arrays_aligned(
    manage_users_token, public_stream, public_group, public_group2
):
    """Onboarding zips the flags against the groups strictly.

    Editing the groups used to leave the arrays at their original length, which
    raised at sign-in and locked the invitee out entirely.
    """
    status, data = api(
        "POST",
        "invitations",
        data={
            "userEmail": str(uuid.uuid4()),
            "streamIDs": [public_stream.id],
            "groupIDs": [public_group.id],
            "groupAdmin": [True],
            "canSave": [True],
            "canSharePhotometry": [True],
        },
        token=manage_users_token,
    )
    assert status == 200
    invitation_id = data["data"]["id"]

    # Add a second group: every array has to grow with it.
    status, _ = api(
        "PATCH",
        f"invitations/{invitation_id}",
        data={"groupIDs": [public_group.id, public_group2.id]},
        token=manage_users_token,
    )
    assert status == 200

    groups, admin, can_save, can_share = invitation_arrays(
        invitation_id, manage_users_token
    )
    assert len(groups) == 2
    for array in (admin, can_save, can_share):
        assert len(array) == len(groups)

    # The original group keeps the flags it was invited with; the new one gets
    # defaults rather than inheriting them.
    first = groups.index(public_group.id)
    second = groups.index(public_group2.id)
    assert admin[first] is True
    assert can_save[first] is True
    assert can_share[first] is True
    assert admin[second] is False
    assert can_save[second] is False
    assert can_share[second] is False

    # Removing a group takes its entry with it.
    status, _ = api(
        "PATCH",
        f"invitations/{invitation_id}",
        data={"groupIDs": [public_group2.id]},
        token=manage_users_token,
    )
    assert status == 200
    groups, admin, can_save, can_share = invitation_arrays(
        invitation_id, manage_users_token
    )
    assert groups == [public_group2.id]
    for array in (admin, can_save, can_share):
        assert len(array) == 1
