import uuid

from tdtax import __version__, taxonomy

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


def test_newsfeed_classification_label_respects_groups(
    upload_data_token,
    super_admin_token,
    view_only_token,
    view_only_token_two_groups,
    public_group,
    public_group2,
):
    """A source's feed label only comes from classifications the reader can see."""
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 235.22,
            "dec": -23.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200, data

    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": f"test taxonomy {uuid.uuid4()}",
            "hierarchy": taxonomy,
            "group_ids": [public_group.id, public_group2.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=super_admin_token,
    )
    assert status == 200, data
    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": obj_id,
            "classification": "Algol",
            "taxonomy_id": data["data"]["taxonomy_id"],
            "probability": 1.0,
            "group_ids": [public_group2.id],
        },
        token=super_admin_token,
    )
    assert status == 200, data

    def source_label(token):
        status, data = api("GET", "newsfeed", token=token, params={"numItems": 1000})
        assert status == 200, data
        items = [
            d
            for d in data["data"]
            if d["type"] == "source" and d["source_id"] == obj_id
        ]
        assert items, data["data"]
        return items[0]["classification"]

    assert source_label(view_only_token_two_groups) == "Algol"
    assert source_label(view_only_token) is None


def test_fail_newsfeed_request_too_many(
    view_only_token,
):
    params = {"numItems": 1001}
    status, data = api("GET", "newsfeed", token=view_only_token, params=params)
    assert status == 400
    assert "numItems should be between 0 and 1000." in data["message"]
