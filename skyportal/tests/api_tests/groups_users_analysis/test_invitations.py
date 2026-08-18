import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.invitations import InvitationPost

from skyportal.tests import client


def test_invite_new_user(manage_users_token, public_stream, public_group):
    client(manage_users_token).post_invitation(
        InvitationPost(
            user_email="string",
            stream_ids=[public_stream.id],
            group_ids=[public_group.id],
            group_admin=[True],
        )
    )


def test_invite_new_user_forbidden(view_only_token, public_stream, public_group):
    with pytest.raises(SkyPortalError, match="Unauthorized") as err:
        client(view_only_token).post_invitation(
            InvitationPost(
                user_email="string",
                stream_ids=[public_stream.id],
                group_ids=[public_group.id],
                group_admin=[True],
            )
        )
    assert err.value.status_code == 401


def test_get_invitations(
    manage_users_token, manage_users_token_group2, public_stream, public_group
):
    invitation_id = (
        client(manage_users_token)
        .post_invitation(
            InvitationPost(
                user_email="string",
                stream_ids=[public_stream.id],
                group_ids=[public_group.id],
                group_admin=[True],
            )
        )
        .id
    )

    # Whoever created the invitation can fetch it
    page = client(manage_users_token).fetch_invitations(group=public_group.name)
    assert page.total_matches == 1
    assert page.invitations[0].id == invitation_id

    # Only invitors can see the invitation
    page = client(manage_users_token_group2).fetch_invitations(group=public_group.name)
    assert page.total_matches == 0


def test_patch_invitation(
    manage_users_token,
    manage_users_token_group2,
    public_stream,
    public_group,
    public_group2,
):
    user_email = str(uuid.uuid4())
    invitation_id = (
        client(manage_users_token)
        .post_invitation(
            InvitationPost(
                user_email=user_email,
                stream_ids=[public_stream.id],
                group_ids=[public_group.id],
                group_admin=[True],
            )
        )
        .id
    )

    # Only the invitor should be able to patch
    with pytest.raises(SkyPortalError, match="Insufficient permissions") as err:
        client(manage_users_token_group2).update_invitation(invitation_id)
    assert err.value.status_code == 400

    # Need one of groupIDs or streamIDs
    with pytest.raises(SkyPortalError, match="At least one of") as err:
        client(manage_users_token).update_invitation(invitation_id)
    assert err.value.status_code == 400

    # Try adding group2 to the invited user
    client(manage_users_token).update_invitation(
        invitation_id, group_ids=[public_group2.id]
    )

    # Try updating role to View only
    client(manage_users_token).update_invitation(invitation_id, role="View only")


def test_delete_invitation(
    manage_users_token,
    manage_users_token_group2,
    public_stream,
    public_group,
    public_group2,
):
    user_email = str(uuid.uuid4())
    invitation_id = (
        client(manage_users_token)
        .post_invitation(
            InvitationPost(
                user_email=user_email,
                stream_ids=[public_stream.id],
                group_ids=[public_group.id],
                group_admin=[True],
            )
        )
        .id
    )

    # Only the invitor should be able to delete
    with pytest.raises(SkyPortalError, match="Insufficient permissions") as err:
        client(manage_users_token_group2).delete_invitation(invitation_id)
    assert err.value.status_code == 400

    # Try deleting invitation
    client(manage_users_token).delete_invitation(invitation_id)
