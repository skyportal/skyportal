import uuid

import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import api, client


def test_post_without_origin_fails(annotation_token, public_source, public_group):
    # this should not work, since no "origin" is given
    # raw api: intentionally malformed payload the typed client can't produce
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
    assert "origin: Field required" in data["message"]

    # this should not work, since "origin" is empty
    with pytest.raises(
        SkyPortalError, match="origin: String should match pattern"
    ) as err:
        client(annotation_token).post_annotation(
            public_source.id,
            "",
            {"offset_from_host_galaxy": 1.5},
            group_ids=[public_group.id],
        )
    assert err.value.status_code == 400


def test_post_same_origin_fails(annotation_token, public_source, public_group):
    sp = client(annotation_token)
    # first time adding an annotation to this object from Kowalski
    sp.post_annotation(
        public_source.id,
        "kowalski",
        {"offset_from_host_galaxy": 1.5},
        group_ids=[public_group.id],
    )

    # this should not work, since "origin" Kowalski was already posted to this object
    # instead, try updating the existing annotation if you have new information!
    with pytest.raises(
        SkyPortalError, match="duplicate key value violates unique constraint"
    ) as err:
        sp.post_annotation(
            public_source.id,
            "kowalski",
            {"offset_from_host_galaxy": 1.5},
            group_ids=[public_group.id],
        )
    assert err.value.status_code in [500, 400]


def test_add_and_retrieve_annotation_group_id(
    annotation_token, public_source, public_group
):
    sp = client(annotation_token)
    annotation_id = sp.post_annotation(
        public_source.id,
        "kowalski",
        {"offset_from_host_galaxy": 1.5},
        group_ids=[public_group.id],
    ).annotation_id

    annotation = sp.fetch_annotation(public_source.id, annotation_id)
    assert annotation.data == {"offset_from_host_galaxy": 1.5}
    assert annotation.origin == "kowalski"


def test_post_annotation_ignores_handler_derived_body_fields(
    annotation_token, public_source
):
    # Clients send obj_id (derived by the handler from the URL) in the body; it
    # must be ignored, not rejected.
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": str(uuid.uuid4()),
            "data": {"numeric_field": 1},
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "PUT",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        data={
            "obj_id": public_source.id,
            "author_id": 1,
            "data": {"numeric_field": 2},
        },
        token=annotation_token,
    )
    assert status == 200


def test_add_and_retrieve_annotation_no_group_id(annotation_token, public_source):
    sp = client(annotation_token)
    annotation_id = sp.post_annotation(
        public_source.id, "kowalski", {"offset_from_host_galaxy": 1.5}
    ).annotation_id

    annotation = sp.fetch_annotation(public_source.id, annotation_id)
    assert annotation.data == {"offset_from_host_galaxy": 1.5}
    assert annotation.origin == "kowalski"


def test_add_and_retrieve_annotation_group_access(
    annotation_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    annotation_token,
):
    sp_two_groups = client(annotation_token_two_groups)
    sp = client(annotation_token)
    annotation_id = sp_two_groups.post_annotation(
        public_source_two_groups.id,
        "kowalski",
        {"offset_from_host_galaxy": 1.5},
        group_ids=[public_group2.id],
    ).annotation_id

    # This token belongs to public_group2
    annotation = sp_two_groups.fetch_annotation(
        public_source_two_groups.id, annotation_id
    )
    assert annotation.data == {"offset_from_host_galaxy": 1.5}
    assert annotation.origin == "kowalski"

    # This token does not belong to public_group2
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(public_source_two_groups.id, annotation_id)
    assert err.value.status_code == 403

    # Both tokens should be able to view this annotation
    annotation_id = sp_two_groups.post_annotation(
        public_source_two_groups.id,
        "GAIA",
        {"offset_from_host_galaxy": 1.5},
        group_ids=[public_group.id, public_group2.id],
    ).annotation_id

    annotation = sp_two_groups.fetch_annotation(
        public_source_two_groups.id, annotation_id
    )
    assert annotation.data == {"offset_from_host_galaxy": 1.5}
    assert annotation.origin == "GAIA"

    annotation = sp.fetch_annotation(public_source_two_groups.id, annotation_id)
    assert annotation.data == {"offset_from_host_galaxy": 1.5}


def test_update_annotation_group_list(
    annotation_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    annotation_token,
):
    sp_two_groups = client(annotation_token_two_groups)
    sp = client(annotation_token)
    annotation_id = sp_two_groups.post_annotation(
        public_source_two_groups.id,
        "kowalski",
        {"offset_from_host_galaxy": 1.5},
        group_ids=[public_group2.id],
    ).annotation_id

    # This token belongs to public_group2
    annotation = sp_two_groups.fetch_annotation(
        public_source_two_groups.id, annotation_id
    )
    assert annotation.origin == "kowalski"
    assert annotation.data == {"offset_from_host_galaxy": 1.5}

    # This token does not belong to public_group2
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(public_source_two_groups.id, annotation_id)
    assert err.value.status_code == 403

    # Both tokens should be able to view annotation after updating group list
    sp_two_groups.update_annotation(
        public_source_two_groups.id,
        annotation_id,
        {"offset_from_host_galaxy": 1.7},
        group_ids=[public_group.id, public_group2.id],
    )

    annotation = sp_two_groups.fetch_annotation(
        public_source_two_groups.id, annotation_id
    )
    assert annotation.data == {"offset_from_host_galaxy": 1.7}

    annotation = sp.fetch_annotation(public_source_two_groups.id, annotation_id)
    assert annotation.data == {"offset_from_host_galaxy": 1.7}


def test_cannot_add_annotation_without_permission(view_only_token, public_source):
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_annotation(
            public_source.id, "kowalski", {"offset_from_host_galaxy": 1.5}
        )
    assert err.value.status_code == 401


def test_obj_annotations(annotation_token, public_source):
    sp = client(annotation_token)
    origin = str(uuid.uuid4())

    annotation_id = sp.post_annotation(
        public_source.id, origin, {"offset_from_host_galaxy": 1.5}
    ).annotation_id

    annotation = sp.fetch_annotation(public_source.id, annotation_id)
    assert annotation.data == {"offset_from_host_galaxy": 1.5}
    assert annotation.origin == origin

    annotations = sp.fetch_annotations(public_source.id)
    assert annotations[0].id == annotation_id
    assert len(annotations) == 1

    # delete should fail if using the wrong object ID
    with pytest.raises(
        SkyPortalError,
        match="Annotation resource ID does not match resource ID given in path",
    ) as err:
        sp.delete_annotation(f"{public_source.id}zzz", annotation_id)
    assert err.value.status_code == 400

    sp.delete_annotation(public_source.id, annotation_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(public_source.id, annotation_id)
    assert err.value.status_code == 403


def test_cannot_add_annotation_without_data(
    annotation_token, public_source, public_group
):
    # raw api: intentionally malformed payload the typed client can't produce
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
    assert "data: Field required" in data["message"]


def test_post_invalid_data(annotation_token, public_source, public_group):
    origin = str(uuid.uuid4())
    # raw api: intentionally malformed payload the typed client can't produce
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
    assert "data: Input should be a valid dictionary" in data["message"]
