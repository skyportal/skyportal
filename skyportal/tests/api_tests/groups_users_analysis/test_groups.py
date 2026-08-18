import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.filters import FilterPost
from skyportal_py.groups import GroupPost

from baselayer.app.env import load_env
from skyportal.model_util import create_token
from skyportal.tests import api, client

_, cfg = load_env()


def test_token_user_create_new_group(super_admin_token, super_admin_user):
    sp = client(super_admin_token)
    group_name = str(uuid.uuid4())
    group_description = "Group description"
    new_group_id = sp.post_group(
        GroupPost(
            name=group_name,
            description=group_description,
            group_admins=[super_admin_user.id],
        )
    ).id

    group = sp.fetch_group(new_group_id)
    assert group.name == group_name
    assert group.description == group_description


def test_cannot_create_group_empty_string_name(manage_groups_token, super_admin_user):
    with pytest.raises(SkyPortalError, match="Missing required parameter") as err:
        client(manage_groups_token).post_group(
            GroupPost(name="", group_admins=[super_admin_user.id])
        )
    assert err.value.status_code == 400


def test_fetch_group_by_name(super_admin_token, super_admin_user):
    group_name = str(uuid.uuid4())
    new_group_id = (
        client(super_admin_token)
        .post_group(GroupPost(name=group_name, group_admins=[super_admin_user.id]))
        .id
    )

    matches = client(super_admin_token).fetch_groups_by_name(group_name)
    assert len(matches) == 1
    assert matches[0].name == group_name
    assert matches[0].id == new_group_id


def test_fetch_group_exclude_users(super_admin_token, public_group):
    group = client(super_admin_token).fetch_group(
        public_group.id, include_group_users=False
    )
    assert group.users is None


def test_token_user_request_all_groups(super_admin_token, super_admin_user):
    sp = client(super_admin_token)
    group_name = str(uuid.uuid4())
    sp.post_group(GroupPost(name=group_name, group_admins=[super_admin_user.id]))

    groups = sp.fetch_groups()
    assert any(user_group.name == group_name for user_group in groups.user_groups)
    assert any(
        group.single_user_group is True and group.name == super_admin_user.username
        for group in groups.user_groups
    )
    assert any(
        user_group.name == group_name for user_group in groups.user_accessible_groups
    )
    assert not any(
        group.single_user_group is True and group.name == super_admin_user.username
        for group in groups.user_accessible_groups
    )


def test_token_user_update_group(super_admin_token, public_group):
    sp = client(super_admin_token)
    new_name = str(uuid.uuid4())
    sp.update_group(public_group.id, new_name)

    assert sp.fetch_group(public_group.id).name == new_name


def test_token_user_delete_group(super_admin_token, public_group):
    sp = client(super_admin_token)
    sp.delete_group(public_group.id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_group(public_group.id)
    assert err.value.status_code == 400


def test_manage_groups_token_get_unowned_group(
    super_admin_token, user, super_admin_user
):
    group_name = str(uuid.uuid4())
    new_group_id = (
        client(super_admin_token)
        .post_group(GroupPost(name=group_name, group_admins=[user.id]))
        .id
    )

    token_name = str(uuid.uuid4())
    token_id = create_token(
        ACLs=["Manage groups"], user_id=super_admin_user.id, name=token_name
    )

    assert client(token_id).fetch_group(new_group_id).name == group_name


def test_public_group(view_only_token):
    group = client(view_only_token).fetch_public_group()
    assert isinstance(group.id, int)


def test_add_delete_stream_group(
    super_admin_token, public_group_no_streams, public_stream
):
    sp = client(super_admin_token)
    added = sp.post_group_stream(public_group_no_streams.id, public_stream.id)
    assert added.stream_id == public_stream.id

    sp.delete_group_stream(public_group_no_streams.id, public_stream.id)


def test_non_su_add_stream_to_group(
    manage_groups_token, public_group_no_streams, public_stream
):
    with pytest.raises(SkyPortalError) as err:
        client(manage_groups_token).post_group_stream(
            public_group_no_streams.id, public_stream.id
        )
    assert err.value.status_code == 400


def test_add_already_added_stream_to_group(
    super_admin_token, public_group_no_streams, public_stream
):
    sp = client(super_admin_token)
    added = sp.post_group_stream(public_group_no_streams.id, public_stream.id)
    assert added.stream_id == public_stream.id

    with pytest.raises(
        SkyPortalError, match="Specified stream is already associated with this group."
    ) as err:
        sp.post_group_stream(public_group_no_streams.id, public_stream.id)
    assert err.value.status_code == 400


def test_add_stream_to_group_delete_stream(
    super_admin_token, public_group_no_streams, public_stream
):
    sp = client(super_admin_token)
    added = sp.post_group_stream(public_group_no_streams.id, public_stream.id)
    assert added.stream_id == public_stream.id

    # check stream is there
    assert sp.fetch_group(public_group_no_streams.id).streams[0].id == public_stream.id

    # delete stream
    sp.delete_stream(public_stream.id)

    # check group still exists and stream is not there
    assert len(sp.fetch_group(public_group_no_streams.id).streams) == 0


def test_post_new_filter_delete_group_deletes_filter(
    super_admin_token, group_with_stream, public_stream
):
    sp = client(super_admin_token)
    filter_id = sp.post_filter(
        FilterPost(
            name=str(uuid.uuid4()),
            stream_id=public_stream.id,
            group_id=group_with_stream.id,
        )
    ).id
    assert sp.fetch_filter(filter_id).id == filter_id

    sp.delete_group(group_with_stream.id)

    with pytest.raises(SkyPortalError, match="Cannot find a filter with ID"):
        sp.fetch_filter(filter_id)


def test_post_new_filter_delete_stream_deletes_filter(
    super_admin_token, group_with_stream, public_stream
):
    sp = client(super_admin_token)
    filter_id = sp.post_filter(
        FilterPost(
            name=str(uuid.uuid4()),
            stream_id=public_stream.id,
            group_id=group_with_stream.id,
        )
    ).id
    assert sp.fetch_filter(filter_id).id == filter_id

    sp.delete_stream(public_stream.id)

    with pytest.raises(SkyPortalError, match="Cannot find a filter with ID"):
        sp.fetch_filter(filter_id)


def test_cannot_delete_sitewide_public_group(super_admin_token):
    sp = client(super_admin_token)
    matches = sp.fetch_groups_by_name(cfg["misc.public_group_name"])
    assert len(matches) == 1
    assert matches[0].name == cfg["misc.public_group_name"]

    with pytest.raises(SkyPortalError, match="Cannot find Group with id"):
        sp.delete_group(matches[0].id)


def test_obj_groups(public_source, public_group, super_admin_token):
    saved_groups = client(super_admin_token).fetch_source_saved_groups(public_source.id)
    assert saved_groups[0].id == public_group.id


def test_add_user_to_group(public_group, user_group2, super_admin_token):
    sp = client(super_admin_token)
    sp.post_group_user(public_group.id, user_group2.id, admin=False, can_save=False)

    group = sp.fetch_group(public_group.id)
    group_user = next((gu for gu in group.users if gu.id == user_group2.id), None)
    assert group_user is not None
    assert not group_user.can_save
    assert not group_user.admin


def test_cannot_add_user_to_group_wout_stream_access(
    public_group_stream2, super_admin_token, user
):
    with pytest.raises(
        SkyPortalError, match="does not have stream access with ID"
    ) as err:
        client(super_admin_token).post_group_user(
            public_group_stream2.id, user.id, admin=False
        )
    assert err.value.status_code == 403


def test_cannot_delete_stream_actively_filtered(
    public_group, public_stream, public_filter, super_admin_token
):
    with pytest.raises(SkyPortalError, match="No stream IDs with") as err:
        client(super_admin_token).delete_group_stream(public_group.id, public_stream.id)
    assert err.value.status_code == 400


def test_delete_stream_not_actively_filtered(
    public_group_two_streams,
    public_group,
    public_stream,
    public_stream2,
    public_filter,
    super_admin_token,
):
    sp = client(super_admin_token)
    # public_stream is actively filtered by public_filter on public_group;
    # the .select(mode="delete") predicate now correctly excludes the row
    # at query time (rather than letting it through and failing at
    # commit-time bulk_verify), so the handler's early return fires.
    # Matches `test_cannot_delete_stream_actively_filtered` above.
    with pytest.raises(SkyPortalError, match="No stream IDs with") as err:
        sp.delete_group_stream(public_group.id, public_stream.id)
    assert err.value.status_code == 400

    sp.delete_group_stream(public_group_two_streams.id, public_stream2.id)


def test_update_group_user_admin_status(public_group, group_admin_token, user):
    sp = client(group_admin_token)
    sp.update_group_user(public_group.id, user.id, admin=True)

    group = sp.fetch_group(public_group.id)
    group_user = next((gu for gu in group.users if gu.id == user.id), None)
    assert group_user is not None
    assert group_user.admin
    assert group_user.can_save


def test_update_group_user_save_access_status(public_group, group_admin_token, user):
    sp = client(group_admin_token)
    sp.update_group_user(public_group.id, user.id, can_save=False)

    group = sp.fetch_group(public_group.id)
    group_user = next((gu for gu in group.users if gu.id == user.id), None)
    assert group_user is not None
    assert not group_user.can_save


def test_non_group_admin_cannot_update_group_user_admin_status(
    public_group, manage_users_token, user
):
    with pytest.raises(SkyPortalError) as err:
        client(manage_users_token).update_group_user(
            public_group.id, user.id, admin=True
        )
    assert err.value.status_code == 400


def test_remove_self_from_group(public_group, view_only_token, user):
    client(view_only_token).delete_group_user(public_group.id, user.id)


def test_super_admin_remove_user_from_group(public_group, super_admin_token, user):
    client(super_admin_token).delete_group_user(public_group.id, user.id)


def test_group_admin_remove_user_from_group(public_group, group_admin_token, user):
    client(group_admin_token).delete_group_user(public_group.id, user.id)


def test_non_group_admin_cannot_remove_user_from_group(
    public_group, view_only_token2, user
):
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token2).delete_group_user(public_group.id, user.id)
    assert err.value.status_code == 403


def test_cannot_add_self_to_group(public_group2, view_only_token, user):
    with pytest.raises(SkyPortalError, match="Unauthorized") as err:
        client(view_only_token).post_group_user(public_group2.id, user.id, admin=False)
    assert err.value.status_code == 401


def test_group_admin_add_user_to_group(public_group, group_admin_token, user_group2):
    client(group_admin_token).post_group_user(
        public_group.id, user_group2.id, admin=False, can_save=True
    )


def test_non_group_admin_cannot_add_user_to_group(
    public_group2, group_admin_token, user
):
    with pytest.raises(SkyPortalError, match="not accessible") as err:
        client(group_admin_token).post_group_user(
            public_group2.id, user.id, admin=False
        )
    assert err.value.status_code == 400


def test_cannot_add_stream_to_single_user_group(super_admin_token, user, public_stream):
    single_user_group = user.single_user_group
    assert single_user_group is not None
    with pytest.raises(SkyPortalError, match="It is a single user group") as err:
        client(super_admin_token).post_group_stream(
            single_user_group.id, public_stream.id
        )
    assert err.value.status_code == 400


def test_cannot_add_another_user_to_single_user_group(user2, super_admin_token, user):
    single_user_group = user2.single_user_group
    assert single_user_group is not None
    with pytest.raises(SkyPortalError, match="It is a single user group") as err:
        client(super_admin_token).post_group_user(
            single_user_group.id, user.id, admin=False
        )
    assert err.value.status_code == 400


def test_cannot_remove_user_from_single_user_group(super_admin_token, user):
    single_user_group = user.single_user_group
    assert single_user_group is not None
    with pytest.raises(SkyPortalError) as err:
        client(super_admin_token).delete_group_user(single_user_group.id, user.id)
    assert err.value.status_code == 403


def test_user_cannot_remove_self_from_single_user_group(view_only_token, user):
    single_user_group = user.single_user_group
    assert single_user_group is not None
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).delete_group_user(single_user_group.id, user.id)
    assert err.value.status_code == 403
