import uuid
from datetime import date, timedelta

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.shifts import ShiftPost

from skyportal.tests import client


def test_add_and_retrieve_comment_on_shift(
    public_group, super_admin_token, comment_token, super_admin_user
):
    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    sp_admin = client(super_admin_token)
    shift_id = sp_admin.post_shift(
        ShiftPost(
            name=name,
            group_id=public_group.id,
            start_date=start_date,
            end_date=end_date,
            description="the Test Shift",
            shift_admins=[super_admin_user.id],
        )
    ).id

    comment_id = sp_admin.post_comment(
        shift_id,
        "Comment on shift text",
        resource_type="shift",
        group_ids=[public_group.id],
    ).comment_id

    comment = client(comment_token).fetch_comment(
        shift_id, comment_id, resource_type="shift"
    )
    assert comment.text == "Comment on shift text"


def test_delete_comment_on_shift(
    comment_token, public_group, super_admin_token, super_admin_user
):
    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    sp_admin = client(super_admin_token)
    shift_id = sp_admin.post_shift(
        ShiftPost(
            name=name,
            group_id=public_group.id,
            start_date=start_date,
            end_date=end_date,
            description="the Test Shift",
            shift_admins=[super_admin_user.id],
        )
    ).id

    comment_id = sp_admin.post_comment(
        shift_id,
        "Comment on shift text",
        resource_type="shift",
        group_ids=[public_group.id],
    ).comment_id

    # try to delete using the wrong object ID
    with pytest.raises(
        SkyPortalError, match="Could not find any accessible comments"
    ) as err:
        client(comment_token).delete_comment(
            f"{shift_id}zzz", comment_id, resource_type="shift"
        )
    assert err.value.status_code == 403

    sp_admin.delete_comment(shift_id, comment_id, resource_type="shift")

    with pytest.raises(SkyPortalError) as err:
        client(comment_token).fetch_comment(shift_id, comment_id, resource_type="shift")
    assert err.value.status_code == 403
