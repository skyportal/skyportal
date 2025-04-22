import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from skyportal.models import ObjTagOption
from skyportal.tests import api


# --- Testing ObjTagOption API
def test_get_tag(super_admin_token):
    tag_to_create = {"name": f"TestTag{uuid.uuid4().hex}"}
    status, _ = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)
    assert status == 200

    status, _ = api("GET", "objtagoption", token=super_admin_token)
    assert status == 200


def test_add_tag_case_sensitive(super_admin_token):
    unique_id = uuid.uuid4().hex
    tag_to_create = {"name": f"TagAdded{unique_id}"}
    status, _ = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)
    assert status == 200

    # Verification that we can't create the same tag twice
    status, _ = api(
        "POST",
        "objtagoption",
        data={"name": f"tagadded{unique_id}"},
        token=super_admin_token,
    )
    assert status == 409

    # Verification that we can't create a tag with a space
    status, _ = api(
        "POST", "objtagoption", data={"name": f"Tag added"}, token=super_admin_token
    )
    assert status == 400

    # Verification that we can't create a tag with an underscore
    status, _ = api(
        "POST", "objtagoption", data={"name": f"tag_added"}, token=super_admin_token
    )
    assert status == 400

    # Verification that we can't create a tag with a dash
    status, _ = api(
        "POST", "objtagoption", data={"name": f"tag-added"}, token=super_admin_token
    )
    assert status == 400


def test_add_tag(super_admin_token):
    tag_to_create = {"name": f"TagAdded{uuid.uuid4().hex}"}
    status, _ = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)
    assert status == 200

    # Verification that we can't create the same tag twice
    status, _ = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)
    assert status == 409

    # Verification that we can't create a tag without a name
    status, _ = api("POST", "objtagoption", data="", token=super_admin_token)
    assert status == 500


def test_modify_tag(super_admin_token):
    # Creation of a tag to modify
    tag_data = {"name": f"TagToModify{uuid.uuid4().hex}"}
    create_status, created_tag = api(
        "POST", "objtagoption", data=tag_data, token=super_admin_token
    )
    assert create_status == 200

    tag_id = created_tag["data"]["id"]
    data = {"name": f"TagRenamed{uuid.uuid4().hex}"}

    # Testing nominal case
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data=data, token=super_admin_token
    )
    assert status == 200

    # Testing to rename a tag with an existing name
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data=data, token=super_admin_token
    )
    assert status == 400

    # Testing to rename a tag without name
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data="", token=super_admin_token
    )
    assert status == 500

    # Testing to rename a non existing tag
    data = {"name": f"tag_not_found_{uuid.uuid4().hex}"}
    status, data = api(
        "PATCH", f"objtagoption/9999999", data=data, token=super_admin_token
    )
    assert status == 404


def test_delete_tag(super_admin_token):
    # Creation of a tag to delete
    tag_data = {"name": f"TagToDelete{uuid.uuid4().hex}"}
    create_status, created_tag = api(
        "POST", "objtagoption", data=tag_data, token=super_admin_token
    )
    assert create_status == 200
    tag_id = created_tag["data"]["id"]

    # Delete the tag
    delete_status, _ = api("DELETE", f"objtagoption/{tag_id}", token=super_admin_token)
    assert delete_status == 200

    # Verification that we can't delete a tag that doesn't exist
    delete_status, _ = api("DELETE", f"objtagoption/{tag_id}", token=super_admin_token)
    assert delete_status == 404


# --- Testing ObjTag API
def test_create_tag_obj_association(super_admin_token):
    # Create a tag option
    tag_data = {"name": f"Tag{uuid.uuid4().hex}"}
    _, tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)

    assoc_data = {"objtagoption_id": tag["data"]["id"], "obj_id": "TIC_114807149"}

    status, data = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 200

    status, data = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 400
    assert "already exists" in data["message"]


def test_update_association(super_admin_token):
    # Create two tags options
    tag1_data = {"name": f"Tag1{uuid.uuid4().hex}"}
    _, tag1 = api("POST", "objtagoption", data=tag1_data, token=super_admin_token)

    tag2_data = {"name": f"Tag2{uuid.uuid4().hex}"}
    _, tag2 = api("POST", "objtagoption", data=tag2_data, token=super_admin_token)

    assoc_data = {"objtagoption_id": tag1["data"]["id"], "obj_id": "TIC_114807149"}
    status, assoc = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 200

    # Testing nominal case
    update_data = {"objtagoption_id": tag2["data"]["id"]}
    status, tag = api(
        "PATCH",
        f"objtag/{assoc['data']['id']}",
        data=update_data,
        token=super_admin_token,
    )

    assert status == 200

    # Testing to modify an association with a non exisiting tag id
    update_data = {"objtagoption_id": 9999999}
    status, data = api(
        "PATCH",
        f"objtag/{assoc['data']['id']}",
        data=update_data,
        token=super_admin_token,
    )
    assert status == 404
    assert "Specified tag does not exist" in data["message"]

    # Testing to modify a non existing association
    update_data = {"objtagoption_id": tag2["data"]["id"]}
    status, data = api(
        "PATCH", "objtag/999999999", data=update_data, token=super_admin_token
    )
    assert status == 404
    assert "Association not found" in data["message"]

    #  Testing to modify an association with a non exisiting obj id
    update_data = {"obj_id": "aaa"}
    status, data = api(
        "PATCH",
        f"objtag/{assoc['data']['id']}",
        data=update_data,
        token=super_admin_token,
    )
    assert status == 404
    assert "Specified obj does not exist" in data["message"]

    # Testing association of the same tag twice to a obj
    update_data = {"obj_id": "TIC_114807149"}
    status, data = api(
        "PATCH",
        f"objtag/{assoc['data']['id']}",
        data=update_data,
        token=super_admin_token,
    )
    assert status == 409
    assert "already exists" in data["message"]


def test_delete_association(super_admin_token):
    tag_data = {"name": f"TagDeleteAssociation{uuid.uuid4().hex}"}
    status, tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    assert status == 200

    assoc_data = {"objtagoption_id": tag["data"]["id"], "obj_id": "TIC_114807149"}
    status, assoc = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 200

    status, _ = api("DELETE", f"objtag/{assoc['data']['id']}", token=super_admin_token)
    assert status == 200

    status, _ = api("DELETE", f"objtag/{assoc['data']['id']}", token=super_admin_token)
    assert status == 404
