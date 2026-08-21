import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client


def test_group_admission_existing_member(user, public_group, upload_data_token):
    with pytest.raises(SkyPortalError, match="already a member of group") as err:
        client(upload_data_token).post_group_admission_request(public_group.id, user.id)
    assert err.value.status_code == 400


def test_group_admission_read_access(
    public_group,
    user_group2,
    upload_data_token,
    upload_data_token_group2,
    manage_sources_token,
    view_only_token,
):
    # Have user_group2 request access to public_group
    request_id = (
        client(upload_data_token_group2)
        .post_group_admission_request(public_group.id, user_group2.id)
        .id
    )

    # user_group2 can read their own request
    client(upload_data_token_group2).fetch_group_admission_request(request_id)

    # group_admin_user is associated with the manages_sources_token and
    # should be able to see the request just submitted
    client(manage_sources_token).fetch_group_admission_request(request_id)

    # Regular user (view_only_token) should not be able to see the request
    # as they are neither a group admin nor the requesting user. RLS now
    # filters them out at the .select() layer, so the handler reports the
    # request as not found rather than running its explicit visibility
    # check.
    with pytest.raises(
        SkyPortalError, match="Could not find an admission request with the ID"
    ) as err:
        client(view_only_token).fetch_group_admission_request(request_id)
    assert err.value.status_code == 400


# test get doesn't exist
def test_group_admission_read_nonexistent(upload_data_token):
    request_id = 9999999
    with pytest.raises(
        SkyPortalError, match="Could not find an admission request with the ID"
    ) as err:
        client(upload_data_token).fetch_group_admission_request(request_id)
    assert err.value.status_code == 400


# test post for someone not me
def test_group_admission_post_for_another_user(
    user_group2, public_group, upload_data_token
):
    with pytest.raises(
        SkyPortalError, match="cannot be made on behalf of others"
    ) as err:
        client(upload_data_token).post_group_admission_request(
            public_group.id, user_group2.id
        )
    assert err.value.status_code == 400


# test patch non-admin
def test_group_admission_patch_permissions(
    public_group,
    user_group2,
    upload_data_token,
    upload_data_token_group2,
    group_admin_token,
):
    # Have user_group2 request access to public_group
    request_id = (
        client(upload_data_token_group2)
        .post_group_admission_request(public_group.id, user_group2.id)
        .id
    )

    # Regular user is not a group admin and cannot approve the request.
    # RLS filters the request out at the .select(mode="update") layer, so
    # the handler reports it as not updatable (same code path as the
    # requesting user trying to approve themselves below).
    with pytest.raises(
        SkyPortalError,
        match="Insufficient permissions: group admission request status can only be changed by group admins",
    ) as err:
        client(upload_data_token).update_group_admission_request(request_id, "accepted")
    assert err.value.status_code == 400

    # Nor can the requesting user do so
    with pytest.raises(
        SkyPortalError,
        match="Insufficient permissions: group admission request status can only be changed by group admins",
    ) as err:
        client(upload_data_token_group2).update_group_admission_request(
            request_id, "accepted"
        )
    assert err.value.status_code == 400

    # The group admin can approve the request
    client(group_admin_token).update_group_admission_request(request_id, "accepted")


# test delete someone else
def test_group_admission_delete_permissions(
    public_group,
    user_group2,
    upload_data_token,
    upload_data_token_group2,
    group_admin_token,
):
    # Have user_group2 request access to public_group
    request_id = (
        client(upload_data_token_group2)
        .post_group_admission_request(public_group.id, user_group2.id)
        .id
    )

    # Regular user cannot delete the request
    with pytest.raises(
        SkyPortalError,
        match="Insufficient permissions: only the requester can delete a group admission request",
    ) as err:
        client(upload_data_token).delete_group_admission_request(request_id)
    assert err.value.status_code == 400

    # Nor can the group admin do so
    with pytest.raises(
        SkyPortalError,
        match="Insufficient permissions: only the requester can delete a group admission request",
    ) as err:
        client(group_admin_token).delete_group_admission_request(request_id)
    assert err.value.status_code == 400

    # The requester can approve the request
    client(upload_data_token_group2).delete_group_admission_request(request_id)


def test_group_admission_auto_accept(
    public_group,
    user_group2,
    upload_data_token_group2,
    group_admin_token,
):
    # A group admin enables auto-accept on the group
    client(group_admin_token).update_group(
        public_group.id, public_group.name, auto_accept_requests=True
    )

    # A non-member requests to join -> should be accepted immediately
    request_id = (
        client(upload_data_token_group2)
        .post_group_admission_request(public_group.id, user_group2.id)
        .id
    )

    # The request is recorded as accepted rather than pending
    request = client(upload_data_token_group2).fetch_group_admission_request(request_id)
    assert request.status == "accepted"

    # ...and the user is now a member of the group
    group = client(group_admin_token).fetch_group(public_group.id)
    assert user_group2.id in [u.id for u in group.users]


def test_group_admission_no_auto_accept_leaves_pending(
    public_group,
    user_group2,
    upload_data_token_group2,
    group_admin_token,
):
    # public_group does not auto-accept by default
    request_id = (
        client(upload_data_token_group2)
        .post_group_admission_request(public_group.id, user_group2.id)
        .id
    )

    request = client(upload_data_token_group2).fetch_group_admission_request(request_id)
    assert request.status == "pending"

    # ...and the user has not been added to the group
    group = client(group_admin_token).fetch_group(public_group.id)
    assert user_group2.id not in [u.id for u in group.users]
