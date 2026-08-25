import uuid

from skyportal.handlers.api.internal.altdata_info import cache as altdata_info_cache
from skyportal.handlers.api.internal.annotations_info import (
    cache as annotations_info_cache,
)
from skyportal.tests import api


def test_altdata_info(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    key = f"key_{uuid.uuid4().hex}"

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 210.0,
            "dec": -22.33,
            "group_ids": [public_group.id],
            "altdata": {key: 1.5},
        },
        token=upload_data_token,
    )
    assert status == 200

    # Clear the (global) cache so the freshly-posted key is reflected.
    del altdata_info_cache["altdata_info"]

    status, data = api("GET", "internal/altdata_info", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    keys = data["data"]["keys"]
    entry = next((e for e in keys if key in e), None)
    assert entry is not None
    assert entry[key] == "number"


def test_annotations_info(upload_data_token, annotation_token, public_group):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 211.0,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    origin = f"origin_{uuid.uuid4().hex}"
    key = f"key_{uuid.uuid4().hex}"
    status, data = api(
        "POST",
        f"sources/{obj_id}/annotations",
        data={"origin": origin, "data": {key: 2.0}},
        token=annotation_token,
    )
    assert status == 200

    # Clear this user's cache so the new annotation is reflected.
    status, profile = api("GET", "internal/profile", token=annotation_token)
    assert status == 200
    del annotations_info_cache[f"annotations_info_{profile['data']['id']}"]

    status, data = api("GET", "internal/annotations_info", token=annotation_token)
    assert status == 200
    assert data["status"] == "success"
    assert origin in data["data"]
    assert any(key in entry for entry in data["data"][origin])
