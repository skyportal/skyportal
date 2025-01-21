import uuid

from skyportal.tests import api


def test_retrieve_newsfeed(view_only_token, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 235.22,
            "dec": -23.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    params = {"numItems": 1000}
    status, data = api("GET", "newsfeed", token=view_only_token, params=params)

    assert status == 200
    data = data["data"]
    assert any(d["type"] == "source" for d in data)
    assert any(d["message"] == "New source saved" for d in data)
    assert any(d["source_id"] == obj_id for d in data)


def test_fail_newsfeed_request_too_many(
    view_only_token,
):
    params = {"numItems": 1001}
    status, data = api("GET", "newsfeed", token=view_only_token, params=params)
    assert status == 400
    assert data["message"] == "numItems should be no larger than 1000."
