import uuid

import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client


def test_token_user_post_new_stream(super_admin_token, public_stream):
    sp = client(super_admin_token)
    stream_id = sp.post_stream(
        str(uuid.uuid4()),
        altdata={"collection": "ZTF_alerts", "selector": [1, 2, 3]},
    ).id

    assert sp.fetch_stream(stream_id).id == stream_id


def test_token_user_update_stream(super_admin_token, public_stream):
    sp = client(super_admin_token)
    new_name = str(uuid.uuid4())
    sp.update_stream(public_stream.id, new_name)

    assert sp.fetch_stream(public_stream.id).name == new_name


def test_token_user_delete_stream(super_admin_token, public_stream):
    sp = client(super_admin_token)
    stream_id = sp.post_stream(
        str(uuid.uuid4()),
        altdata={"collection": "ZTF_alerts", "selector": [1, 2, 3]},
    ).id

    sp.delete_stream(stream_id)


def test_super_admin_grant_delete_user_stream_access(
    super_admin_token, user, public_stream2
):
    sp = client(super_admin_token)
    sp.post_stream_user(public_stream2.id, user.id)
    sp.delete_stream_user(public_stream2.id, user.id)


def test_group_admin_cannot_grant_delete_user_stream_access(
    group_admin_token, user, public_stream, public_stream2
):
    sp = client(group_admin_token)
    # Non-admins cannot grant access to other users (public_stream2 is not
    # auto-join), so the handler rejects the request.
    with pytest.raises(SkyPortalError, match="Insufficient permissions") as err:
        sp.post_stream_user(public_stream2.id, user.id)
    assert err.value.status_code == 400

    with pytest.raises(SkyPortalError) as err:
        sp.delete_stream_user(public_stream.id, user.id)
    assert err.value.status_code == 401


def test_user_cannot_grant_self_stream_access(view_only_token, user, public_stream2):
    # public_stream2 is not auto-join, so a user cannot add themselves.
    with pytest.raises(SkyPortalError, match="Insufficient permissions") as err:
        client(view_only_token).post_stream_user(public_stream2.id, user.id)
    assert err.value.status_code == 400


def test_auto_join_stream_visible_to_non_member(
    super_admin_token, view_only_token, user, public_stream2
):
    sp = client(view_only_token)
    # public_stream2 is not one of the user's streams and is not auto-join, so
    # the user cannot see it...
    with pytest.raises(SkyPortalError, match="Could not retrieve stream") as err:
        sp.fetch_stream(public_stream2.id)
    assert err.value.status_code == 400

    assert public_stream2.id not in [s.id for s in sp.fetch_streams()]

    # ...but once flagged auto-join it becomes visible (for discovery/joining),
    # even though the user is not yet a member.
    client(super_admin_token).update_stream(
        public_stream2.id, public_stream2.name, auto_join=True
    )

    stream = sp.fetch_stream(public_stream2.id)
    assert stream.id == public_stream2.id
    assert stream.auto_join is True

    assert public_stream2.id in [s.id for s in sp.fetch_streams()]


def test_user_can_self_join_auto_join_stream(
    super_admin_token, view_only_token, user, public_stream2
):
    # Flag the stream as auto-join
    client(super_admin_token).update_stream(
        public_stream2.id, public_stream2.name, auto_join=True
    )

    # The user can now add themselves
    sp = client(view_only_token)
    sp.post_stream_user(public_stream2.id, user.id)

    # ...and the stream is now readable by (accessible to) the user
    assert sp.fetch_stream(public_stream2.id).id == public_stream2.id

    # ...and shows up among the user's own streams in their profile
    assert public_stream2.id in [s.id for s in sp.fetch_profile().streams]


def test_user_cannot_add_other_user_to_auto_join_stream(
    super_admin_token, view_only_token, user2, public_stream2
):
    # Even on an auto-join stream, a non-admin may add only themselves.
    client(super_admin_token).update_stream(
        public_stream2.id, public_stream2.name, auto_join=True
    )

    with pytest.raises(SkyPortalError, match="Insufficient permissions") as err:
        client(view_only_token).post_stream_user(public_stream2.id, user2.id)
    assert err.value.status_code == 400
