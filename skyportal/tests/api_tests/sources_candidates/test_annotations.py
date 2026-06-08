import uuid

from skyportal.tests import api


def test_post_without_origin_fails(annotation_token, public_source, public_group):
    # this should not work, since no "origin" is given
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )

    assert status in [400]
    assert "origin must be specified" in data["message"]

    # this should not work, since "origin" is empty
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": "",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )

    assert status == 400
    assert "Input `origin` must begin with alphanumeric/underscore" in data["message"]


def test_post_same_origin_fails(annotation_token, public_source, public_group):
    # first time adding an annotation to this object from Kowalski
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )

    assert status == 200

    # this should not work, since "origin" Kowalski was already posted to this object
    # instead, try updating the existing annotation if you have new information!
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )

    assert status in [500, 400]
    assert "duplicate key value violates unique constraint" in data["message"]


def test_add_and_retrieve_annotation_group_id(
    annotation_token, public_source, public_group
):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    status, data = api(
        "GET",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        token=annotation_token,
    )

    assert status == 200
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.5}
    assert data["data"]["origin"] == "kowalski"


def test_add_and_retrieve_annotation_no_group_id(annotation_token, public_source):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    status, data = api(
        "GET",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        token=annotation_token,
    )

    assert status == 200
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.5}
    assert data["data"]["origin"] == "kowalski"


def test_add_and_retrieve_annotation_group_access(
    annotation_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    annotation_token,
):
    status, data = api(
        "POST",
        f"sources/{public_source_two_groups.id}/annotations",
        data={
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group2.id],
        },
        token=annotation_token_two_groups,
    )

    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    # This token belongs to public_group2
    status, data = api(
        "GET",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        token=annotation_token_two_groups,
    )
    assert status == 200
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.5}
    assert data["data"]["origin"] == "kowalski"

    # This token does not belong to public_group2
    status, data = api(
        "GET",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 403

    # Both tokens should be able to view this annotation
    status, data = api(
        "POST",
        f"sources/{public_source_two_groups.id}/annotations",
        data={
            "origin": "GAIA",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id, public_group2.id],
        },
        token=annotation_token_two_groups,
    )

    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    status, data = api(
        "GET",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        token=annotation_token_two_groups,
    )
    assert status == 200
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.5}
    assert data["data"]["origin"] == "GAIA"

    status, data = api(
        "GET",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 200
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.5}


def test_update_annotation_group_list(
    annotation_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    annotation_token,
):
    status, data = api(
        "POST",
        f"sources/{public_source_two_groups.id}/annotations",
        data={
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group2.id],
        },
        token=annotation_token_two_groups,
    )
    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    # This token belongs to public_group2
    status, data = api(
        "GET",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        token=annotation_token_two_groups,
    )
    assert status == 200
    assert data["data"]["origin"] == "kowalski"
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.5}

    # This token does not belong to public_group2
    status, data = api(
        "GET",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 403

    # Both tokens should be able to view annotation after updating group list
    status, data = api(
        "PUT",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        data={
            "data": {"offset_from_host_galaxy": 1.7},
            "group_ids": [public_group.id, public_group2.id],
        },
        token=annotation_token_two_groups,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        token=annotation_token_two_groups,
    )
    assert status == 200
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.7}

    status, data = api(
        "GET",
        f"sources/{public_source_two_groups.id}/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 200
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.7}


def test_cannot_add_annotation_without_permission(view_only_token, public_source):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
        },
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"


def test_delete_annotation(annotation_token, public_source):
    origin = str(uuid.uuid4())

    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": origin,
            "data": {"offset_from_host_galaxy": 1.5},
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    status, data = api(
        "GET",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 200
    assert data["data"]["data"] == {"offset_from_host_galaxy": 1.5}
    assert data["data"]["origin"] == origin

    # delete should fail if using the wrong object ID
    status, data = api(
        "DELETE",
        f"sources/{public_source.id}zzz/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 400
    assert (
        "Annotation resource ID does not match resource ID given in path"
        in data["message"]
    )

    status, data = api(
        "DELETE",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 403


def test_obj_annotations(annotation_token, public_source, public_group):
    origin = str(uuid.uuid4())

    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": origin,
            "data": {"offset_from_host_galaxy": 1.5},
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    status, data = api(
        "GET",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{public_source.id}/annotations", token=annotation_token
    )
    assert status == 200
    assert data["data"][0]["id"] == annotation_id
    assert len(data["data"]) == 1


def test_cannot_add_annotation_without_data(
    annotation_token, public_source, public_group
):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": "kowalski",
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )
    assert status == 400
    assert (
        "Invalid data: the annotation data must be an object with at least one {key: value} pair"
        in data["message"]
    )


def test_post_invalid_data(annotation_token, public_source, public_group):
    origin = str(uuid.uuid4())
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "data": "Test",
            "origin": origin,
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )

    assert status == 400
    assert "Invalid data" in data["message"]


def test_fetch_all_annotations_on_obj(annotation_token, public_source, public_group):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{public_source.id}/annotations",
        token=annotation_token,
    )

    assert status == 200
    assert len(data["data"]) == 1
    assert data["data"][0]["data"] == {"offset_from_host_galaxy": 1.5}
    assert data["data"][0]["origin"] == "kowalski"
