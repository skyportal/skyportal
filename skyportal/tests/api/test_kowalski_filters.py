import uuid
from skyportal.tests import api


def test_post_patch_kowalski_filter_version(super_admin_token, public_filter):
    status, data = api("GET", f"filters/{public_filter.id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"] for k in ["name", "group_id", "stream_id"])

    stream_id = data["data"]["stream_id"]

    # factory-generated test streams lack necessary altdata
    status, data = api(
        "PATCH",
        f"streams/{stream_id}",
        data={
            "name": str(uuid.uuid4()),
            "altdata": {"collection": "ZTF_alerts", "selector": [1, 2]},
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    pipeline = [{"$match": {"candidate.drb": {"$gt": 0.999999}}}]
    status, data = api(
        "POST",
        f"filters/{public_filter.id}/v",
        data={"pipeline": pipeline},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}/v",
        data={"active": False, "autosave": True, "update_annotations": True},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert not data["data"]["active"]
    assert data["data"]["autosave"]
    assert data["data"]["update_annotations"]
