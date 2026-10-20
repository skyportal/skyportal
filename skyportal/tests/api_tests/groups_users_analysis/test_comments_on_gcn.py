import sqlalchemy as sa

from skyportal.models import DBSession, UserNotification
from skyportal.tests import api


def test_add_and_retrieve_comment_on_gcn(
    comment_token, upload_data_token, public_group, super_admin_token, gcn_GW190425
):
    gcnevent_id = gcn_GW190425.id

    status, data = api(
        "POST",
        f"gcn_event/{gcnevent_id}/comments",
        data={
            "text": "Comment text",
            "group_ids": [public_group.id],
        },
        token=comment_token,
    )
    assert status == 200
    comment_id = data["data"]["comment_id"]

    status, data = api(
        "GET", f"gcn_event/{gcnevent_id}/comments/{comment_id}", token=comment_token
    )

    assert status == 200
    assert data["data"]["text"] == "Comment text"


def test_delete_comment_on_gcn(
    comment_token, public_group, super_admin_token, gcn_GW190425
):
    gcnevent_id = gcn_GW190425.id

    status, data = api(
        "POST",
        f"gcn_event/{gcnevent_id}/comments",
        data={"text": "Comment text"},
        token=comment_token,
    )
    assert status == 200
    comment_id = data["data"]["comment_id"]

    status, data = api(
        "GET", f"gcn_event/{gcnevent_id}/comments/{comment_id}", token=comment_token
    )
    assert status == 200
    assert data["data"]["text"] == "Comment text"

    # try to delete using the wrong object ID
    status, data = api(
        "DELETE",
        f"gcn_event/{gcnevent_id}zzz/comments/{comment_id}",
        token=comment_token,
    )
    assert status == 400
    assert (
        "Comment resource ID does not match resource ID given in path"
        in data["message"]
    )

    status, data = api(
        "DELETE",
        f"gcn_event/{gcnevent_id}/comments/{comment_id}",
        token=comment_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"gcn_event/{gcnevent_id}/comments/{comment_id}", token=comment_token
    )
    assert status == 403


def test_mention_in_comment_on_gcn_links_to_event_page(
    comment_token, public_group, view_only_user, gcn_GW190425
):
    view_only_user.preferences = {"notifications": {"mention": {"active": True}}}
    DBSession().commit()
    dateobs = gcn_GW190425.dateobs.isoformat()

    status, data = api(
        "POST",
        f"gcn_event/{gcn_GW190425.id}/comments",
        data={
            "text": f"@{view_only_user.username} take a look",
            "group_ids": [public_group.id],
        },
        token=comment_token,
    )
    assert status == 200, data

    DBSession().expire_all()
    notification = DBSession().scalar(
        sa.select(UserNotification).where(
            UserNotification.user_id == view_only_user.id,
            UserNotification.notification_type == "mention",
        )
    )
    # the frontend routes GCN events by dateobs, not by their integer id
    assert notification.url == f"/gcn_events/{dateobs}"
    assert f"*{dateobs}*" in notification.text
