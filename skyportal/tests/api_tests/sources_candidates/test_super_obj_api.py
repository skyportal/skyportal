import uuid

from skyportal.tests import api


def test_super_obj_create_and_retrieve(
    super_admin_token, public_source, public_source_two_groups
):
    name = f"asteroid-{uuid.uuid4().hex}"
    status, data = api(
        "POST",
        "super_objs",
        data={
            "name": name,
            "is_roid": True,
            "obj_ids": [public_source.id, public_source_two_groups.id],
        },
        token=super_admin_token,
    )
    assert status == 200
    super_obj_id = data["data"]["id"]

    status, data = api("GET", f"super_objs/{super_obj_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["name"] == name
    assert data["data"]["is_roid"] is True
    assert {obj["id"] for obj in data["data"]["objs"]} == {
        public_source.id,
        public_source_two_groups.id,
    }


def test_super_obj_filters(super_admin_token, public_source):
    name = f"asteroid-{uuid.uuid4().hex}"
    status, data = api(
        "POST",
        "super_objs",
        data={"name": name, "is_roid": True, "obj_ids": [public_source.id]},
        token=super_admin_token,
    )
    assert status == 200
    super_obj_id = data["data"]["id"]

    status, data = api("GET", f"super_objs?name={name}", token=super_admin_token)
    assert status == 200
    assert [s["id"] for s in data["data"]] == [super_obj_id]

    status, data = api(
        "GET", f"super_objs?objID={public_source.id}", token=super_admin_token
    )
    assert status == 200
    assert super_obj_id in [s["id"] for s in data["data"]]

    status, data = api(
        "GET", f"super_objs?name={name}&isRoid=false", token=super_admin_token
    )
    assert status == 200
    assert data["data"] == []


def test_super_obj_membership_updates(
    super_admin_token, public_source, public_source_two_groups
):
    status, data = api(
        "POST",
        "super_objs",
        data={"name": f"asteroid-{uuid.uuid4().hex}", "obj_ids": [public_source.id]},
        token=super_admin_token,
    )
    assert status == 200
    super_obj_id = data["data"]["id"]

    status, _ = api(
        "PATCH",
        f"super_objs/{super_obj_id}",
        data={"add_obj_ids": [public_source_two_groups.id]},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"super_objs/{super_obj_id}", token=super_admin_token)
    assert {obj["id"] for obj in data["data"]["objs"]} == {
        public_source.id,
        public_source_two_groups.id,
    }

    # adding the same Obj again must not duplicate it
    status, _ = api(
        "PATCH",
        f"super_objs/{super_obj_id}",
        data={"add_obj_ids": [public_source_two_groups.id]},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"super_objs/{super_obj_id}", token=super_admin_token)
    assert len(data["data"]["objs"]) == 2

    status, _ = api(
        "PATCH",
        f"super_objs/{super_obj_id}",
        data={"remove_obj_ids": [public_source.id]},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"super_objs/{super_obj_id}", token=super_admin_token)
    assert [obj["id"] for obj in data["data"]["objs"]] == [public_source_two_groups.id]


def test_super_obj_rejects_conflicting_membership_args(
    super_admin_token, public_source
):
    status, data = api(
        "POST",
        "super_objs",
        data={"name": f"asteroid-{uuid.uuid4().hex}"},
        token=super_admin_token,
    )
    assert status == 200
    super_obj_id = data["data"]["id"]

    status, data = api(
        "PATCH",
        f"super_objs/{super_obj_id}",
        data={"obj_ids": [public_source.id], "add_obj_ids": [public_source.id]},
        token=super_admin_token,
    )
    assert status == 400


def test_super_obj_rejects_unknown_obj(super_admin_token):
    status, data = api(
        "POST",
        "super_objs",
        data={"name": f"asteroid-{uuid.uuid4().hex}", "obj_ids": ["does-not-exist"]},
        token=super_admin_token,
    )
    assert status == 400


def test_super_obj_delete_leaves_objs(super_admin_token, public_source):
    """Deleting a SuperObj must not delete the Objs it links."""
    status, data = api(
        "POST",
        "super_objs",
        data={"name": f"asteroid-{uuid.uuid4().hex}", "obj_ids": [public_source.id]},
        token=super_admin_token,
    )
    assert status == 200
    super_obj_id = data["data"]["id"]

    status, _ = api("DELETE", f"super_objs/{super_obj_id}", token=super_admin_token)
    assert status == 200

    status, _ = api("GET", f"super_objs/{super_obj_id}", token=super_admin_token)
    assert status == 400

    status, data = api("GET", f"sources/{public_source.id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["id"] == public_source.id


def test_super_obj_delete_requires_admin(
    super_admin_token, upload_data_token, public_source
):
    status, data = api(
        "POST",
        "super_objs",
        data={"name": f"asteroid-{uuid.uuid4().hex}", "obj_ids": [public_source.id]},
        token=upload_data_token,
    )
    assert status == 200
    super_obj_id = data["data"]["id"]

    status, _ = api("DELETE", f"super_objs/{super_obj_id}", token=upload_data_token)
    assert status == 401

    status, _ = api("DELETE", f"super_objs/{super_obj_id}", token=super_admin_token)
    assert status == 200
