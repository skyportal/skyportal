import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client


def test_add_and_retrieve_comment_on_gcn(
    comment_token, upload_data_token, public_group, super_admin_token, gcn_GW190425
):
    gcnevent_id = gcn_GW190425.id

    sp = client(comment_token)
    comment_id = sp.post_comment(
        gcnevent_id,
        "Comment text",
        resource_type="gcn_event",
        group_ids=[public_group.id],
    ).comment_id

    comment = sp.fetch_comment(gcnevent_id, comment_id, resource_type="gcn_event")
    assert comment.text == "Comment text"


def test_delete_comment_on_gcn(
    comment_token, public_group, super_admin_token, gcn_GW190425
):
    gcnevent_id = gcn_GW190425.id

    sp = client(comment_token)
    comment_id = sp.post_comment(
        gcnevent_id, "Comment text", resource_type="gcn_event"
    ).comment_id

    comment = sp.fetch_comment(gcnevent_id, comment_id, resource_type="gcn_event")
    assert comment.text == "Comment text"

    # try to delete using the wrong object ID
    with pytest.raises(
        SkyPortalError,
        match="Comment resource ID does not match resource ID given in path",
    ) as err:
        sp.delete_comment(f"{gcnevent_id}zzz", comment_id, resource_type="gcn_event")
    assert err.value.status_code == 400

    sp.delete_comment(gcnevent_id, comment_id, resource_type="gcn_event")

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_comment(gcnevent_id, comment_id, resource_type="gcn_event")
    assert err.value.status_code == 403
