import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from skyportal.models import ObjTagOption
from skyportal.tests import api


# --- Testing ObjTagOption API
def test_get_tag(super_admin_token):
    tag_to_create = {"name": f"TestTag{uuid.uuid4().hex}"}
    status, data = api(
        "POST", "objtagoption", data=tag_to_create, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", "objtagoption", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    tag_names = [tag["name"] for tag in data["data"]]
    assert tag_to_create["name"] in tag_names


@pytest.mark.parametrize(
    "invalid_tag_name",
    [
        "Tag added",
        "tag_added",
        "tag-added",
    ],
)
def test_add_tag_case_sensitive(super_admin_token, invalid_tag_name):
    status, data = api(
        "POST", "objtagoption", data={"name": invalid_tag_name}, token=super_admin_token
    )

    assert status == 400
    assert data["status"] == "error"
    assert "must contain only letters and numbers" in data["message"]


@pytest.mark.parametrize(
    "color, expected_status, should_be_valid",
    [
        # Valid colors
        ("#000000", 200, True),  # Black
        ("#ffffff", 200, True),  # White (lowercase)
        ("#FFFFFF", 200, True),  # White (uppercase)
        ("#3a87ad", 200, True),  # Blue
        ("#ff6b6b", 200, True),  # Red
        (None, 200, True),  # Null color (valid)
        ("", 200, True),
        # Invalid colors
        ("#12345", 400, False),  # Too short
        ("#1234567", 400, False),  # Too long
        ("3a87ad", 400, False),  # Missing #
        ("#GGGGGG", 400, False),  # Invalid hex characters
        ("#3a87aD1", 400, False),  # Too long with valid hex
        ("blue", 400, False),  # Color name instead of hex
        ("#", 400, False),  # Just hash
        ("rgb(255,0,0)", 400, False),  # RGB format
        ("hsl(0,100%,50%)", 400, False),  # HSL format
    ],
)
def test_tag_color_validation(
    super_admin_token, color, expected_status, should_be_valid
):
    """Test creating tags with valid and invalid color values"""
    tag_data = {"name": f"TestTag{uuid.uuid4().hex}", "color": color}

    status, data = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    assert status == expected_status

    if should_be_valid:
        assert data["status"] == "success"
        assert data["data"]["name"] == tag_data["name"]
        assert data["data"]["color"] == color
    else:
        assert data["status"] == "error"
        assert "must be a valid hex color code" in data["message"]


def test_add_tag(super_admin_token):
    tag_to_create = {"name": f"TagAdded{uuid.uuid4().hex}"}
    status, data = api(
        "POST", "objtagoption", data=tag_to_create, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["name"] == tag_to_create["name"]

    # Verification that we can't create the same tag twice
    status, data = api(
        "POST", "objtagoption", data=tag_to_create, token=super_admin_token
    )
    assert status == 409
    assert data["status"] == "error"
    assert "already exists" in data["message"]

    # Verification that we can't create a tag without a name
    status, data = api("POST", "objtagoption", data="", token=super_admin_token)
    assert status == 500
    assert data["status"] == "error"
    assert "Please ensure posted data is of type application/json" in data["message"]


def test_modify_tag(super_admin_token):
    # Creation of a tag to modify
    tag_data = {"name": f"TagToModify{uuid.uuid4().hex}"}
    create_status, created_tag = api(
        "POST", "objtagoption", data=tag_data, token=super_admin_token
    )
    assert create_status == 200
    assert created_tag["status"] == "success"

    tag_id = created_tag["data"]["id"]
    tag_to_rename = {"name": f"TagRenamed{uuid.uuid4().hex}"}

    # Testing nominal case
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data=tag_to_rename, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    # Testing to rename a tag with an existing name
    tag_to_create = {"name": f"TagAdded{uuid.uuid4().hex}"}
    status, data = api(
        "POST", "objtagoption", data=tag_to_create, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data=tag_to_create, token=super_admin_token
    )
    assert status == 400
    assert data["status"] == "error"
    assert "This tag name already exists for another tag" in data["message"]

    # Testing to rename a tag without name
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data="", token=super_admin_token
    )
    assert status == 500
    assert data["status"] == "error"
    assert "Please ensure posted data is of type application/json" in data["message"]

    # Testing to rename a non existing tag
    data = {"name": f"tag_not_found_{uuid.uuid4().hex}"}
    status, data = api(
        "PATCH", f"objtagoption/9999999", data=data, token=super_admin_token
    )
    assert status == 404
    assert data["status"] == "error"
    assert "Tag not found" in data["message"]


def test_modify_tag_without_providing_color(super_admin_token):
    """Test setting tag color back to null"""
    tag_data = {"name": f"TagColorToNull{uuid.uuid4().hex}", "color": "#3a87ad"}
    create_status, created_tag = api(
        "POST", "objtagoption", data=tag_data, token=super_admin_token
    )
    assert create_status == 200
    tag_id = created_tag["data"]["id"]

    # Update without providing color (should keep existing color)
    update_data = {"name": tag_data["name"]}
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data=update_data, token=super_admin_token
    )
    assert status == 200

    status, data = api("GET", "objtagoption", token=super_admin_token)
    updated_tag = next((tag for tag in data["data"] if tag["id"] == tag_id), None)
    assert updated_tag["color"] == "#3a87ad"


def test_change_tag_color(super_admin_token):
    """Test changing the color of an existing tag"""
    initial_color = "#ff0000"
    tag_data = {"name": f"TagColorChange{uuid.uuid4().hex}", "color": initial_color}
    create_status, created_tag = api(
        "POST", "objtagoption", data=tag_data, token=super_admin_token
    )
    assert create_status == 200
    assert created_tag["status"] == "success"
    assert created_tag["data"]["color"] == initial_color

    tag_id = created_tag["data"]["id"]

    new_color = "#3a87ad"
    update_data = {"name": tag_data["name"], "color": new_color}
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data=update_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    # Verify the color was changed
    status, data = api("GET", "objtagoption", token=super_admin_token)
    assert status == 200
    updated_tag = next((tag for tag in data["data"] if tag["id"] == tag_id), None)
    assert updated_tag is not None
    assert updated_tag["color"] == new_color


def test_delete_tag(super_admin_token):
    # Creation of a tag to delete
    tag_data = {"name": f"TagToDelete{uuid.uuid4().hex}"}
    create_status, created_tag = api(
        "POST", "objtagoption", data=tag_data, token=super_admin_token
    )
    assert create_status == 200
    assert created_tag["status"] == "success"

    tag_id = created_tag["data"]["id"]

    # Delete the tag
    delete_status, data = api(
        "DELETE", f"objtagoption/{tag_id}", token=super_admin_token
    )
    assert delete_status == 200
    assert created_tag["status"] == "success"
    assert "Successfully deleted tag" in data["data"]

    # Verification that we can't delete a tag that doesn't exist
    delete_status, data = api(
        "DELETE", f"objtagoption/{tag_id}", token=super_admin_token
    )
    assert delete_status == 404
    assert data["status"] == "error"
    assert "Tag not found" in data["message"]


# --- Testing ObjTag API
def test_create_tag_obj_association(super_admin_token, public_source):
    # Create a tag option
    tag_data = {"name": f"Tag{uuid.uuid4().hex}"}
    status, tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    assert status == 200
    assert tag["status"] == "success"

    assoc_data = {"objtagoption_id": tag["data"]["id"], "obj_id": public_source.id}

    status, data = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assoc_id = data["data"]["id"]

    status, data = api("GET", "objtag", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    created_assoc = next(
        (assoc for assoc in data["data"] if assoc["id"] == assoc_id), None
    )
    assert created_assoc is not None

    assert created_assoc["objtagoption_id"] == tag["data"]["id"]
    assert created_assoc["obj_id"] == public_source.id

    status, data = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 400
    assert data["status"] == "error"
    assert "already exists" in data["message"]


def test_delete_association(super_admin_token, public_source):
    tag_data = {"name": f"TagDeleteAssociation{uuid.uuid4().hex}"}
    status, tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    assert status == 200
    assert tag["status"] == "success"

    assoc_data = {"objtagoption_id": tag["data"]["id"], "obj_id": public_source.id}
    status, assoc = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 200
    assert assoc["status"] == "success"

    status, data = api(
        "DELETE", f"objtag/{assoc['data']['id']}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert "Successfully deleted association" in data["data"]

    status, data = api(
        "DELETE", f"objtag/{assoc['data']['id']}", token=super_admin_token
    )
    assert status == 404
    assert data["status"] == "error"
    assert "Association not found" in data["message"]
