import uuid

import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import api, client


# --- Testing ObjTagOption API
def test_get_tag(super_admin_token):
    sp = client(super_admin_token)
    tag_name = f"TestTag{uuid.uuid4().hex}"
    sp.post_obj_tag_option(tag_name)

    tag_names = [tag.name for tag in sp.fetch_obj_tag_options()]
    assert tag_name in tag_names


@pytest.mark.parametrize(
    "invalid_tag_name",
    [
        "Tag added",
        "tag_added",
        "tag-added",
    ],
)
def test_add_tag_case_sensitive(super_admin_token, invalid_tag_name):
    with pytest.raises(
        SkyPortalError, match="must contain only letters and numbers"
    ) as err:
        client(super_admin_token).post_obj_tag_option(invalid_tag_name)
    assert err.value.status_code == 400


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
    sp = client(super_admin_token)
    tag_name = f"TestTag{uuid.uuid4().hex}"

    if should_be_valid:
        tag = sp.post_obj_tag_option(tag_name, color=color)
        assert tag.name == tag_name
        assert tag.color == color
    else:
        with pytest.raises(
            SkyPortalError, match="must be a valid hex color code"
        ) as err:
            sp.post_obj_tag_option(tag_name, color=color)
        assert err.value.status_code == expected_status


def test_add_tag(super_admin_token):
    sp = client(super_admin_token)
    tag_name = f"TagAdded{uuid.uuid4().hex}"
    tag = sp.post_obj_tag_option(tag_name)
    assert tag.name == tag_name

    # Verification that we can't create the same tag twice
    with pytest.raises(SkyPortalError, match="already exists") as err:
        sp.post_obj_tag_option(tag_name)
    assert err.value.status_code == 409

    # Verification that we can't create a tag without a name
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api("POST", "objtagoption", data="", token=super_admin_token)
    assert status == 500
    assert data["status"] == "error"
    assert "Please ensure posted data is of type application/json" in data["message"]


def test_modify_tag(super_admin_token):
    sp = client(super_admin_token)
    # Creation of a tag to modify
    tag_id = sp.post_obj_tag_option(f"TagToModify{uuid.uuid4().hex}").id

    # Testing nominal case
    sp.update_obj_tag_option(tag_id, f"TagRenamed{uuid.uuid4().hex}")

    # Testing to rename a tag with an existing name
    existing_name = f"TagAdded{uuid.uuid4().hex}"
    sp.post_obj_tag_option(existing_name)
    with pytest.raises(
        SkyPortalError, match="This tag name already exists for another tag"
    ) as err:
        sp.update_obj_tag_option(tag_id, existing_name)
    assert err.value.status_code == 400

    # Testing to rename a tag without name
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "PATCH", f"objtagoption/{tag_id}", data="", token=super_admin_token
    )
    assert status == 500
    assert data["status"] == "error"
    assert "Please ensure posted data is of type application/json" in data["message"]

    # Testing to rename a non existing tag
    with pytest.raises(SkyPortalError, match="Tag not found") as err:
        sp.update_obj_tag_option(9999999, f"TagNotFound{uuid.uuid4().hex}")
    assert err.value.status_code == 404


def test_modify_tag_without_providing_color(super_admin_token):
    """Test setting tag color back to null"""
    sp = client(super_admin_token)
    tag_name = f"TagColorToNull{uuid.uuid4().hex}"
    tag_id = sp.post_obj_tag_option(tag_name, color="#3a87ad").id

    # Update without providing color (should keep existing color)
    sp.update_obj_tag_option(tag_id, tag_name)

    updated_tag = next(
        (tag for tag in sp.fetch_obj_tag_options() if tag.id == tag_id), None
    )
    assert updated_tag.color == "#3a87ad"


def test_change_tag_color(super_admin_token):
    """Test changing the color of an existing tag"""
    sp = client(super_admin_token)
    initial_color = "#ff0000"
    tag_name = f"TagColorChange{uuid.uuid4().hex}"
    created_tag = sp.post_obj_tag_option(tag_name, color=initial_color)
    assert created_tag.color == initial_color

    tag_id = created_tag.id

    new_color = "#3a87ad"
    sp.update_obj_tag_option(tag_id, tag_name, color=new_color)

    # Verify the color was changed
    updated_tag = next(
        (tag for tag in sp.fetch_obj_tag_options() if tag.id == tag_id), None
    )
    assert updated_tag is not None
    assert updated_tag.color == new_color


def test_delete_tag(super_admin_token):
    sp = client(super_admin_token)
    # Creation of a tag to delete
    tag_id = sp.post_obj_tag_option(f"TagToDelete{uuid.uuid4().hex}").id

    # Delete the tag
    sp.delete_obj_tag_option(tag_id)

    # Verification that we can't delete a tag that doesn't exist
    with pytest.raises(SkyPortalError, match="Tag not found") as err:
        sp.delete_obj_tag_option(tag_id)
    assert err.value.status_code == 404


# --- Testing ObjTag API
def test_create_tag_obj_association(super_admin_token, public_source, public_group):
    sp = client(super_admin_token)
    # Create a tag option
    tag = sp.post_obj_tag_option(f"Tag{uuid.uuid4().hex}")

    assoc_id = sp.post_obj_tag(public_source.id, tag.id, group_ids=[public_group.id]).id

    created_assoc = next(
        (assoc for assoc in sp.fetch_obj_tags() if assoc.id == assoc_id), None
    )
    assert created_assoc is not None

    assert created_assoc.objtagoption_id == tag.id
    assert created_assoc.obj_id == public_source.id

    sp.post_obj_tag(public_source.id, tag.id, group_ids=[public_group.id])


def test_delete_association(super_admin_token, public_source, public_group):
    sp = client(super_admin_token)
    tag = sp.post_obj_tag_option(f"TagDeleteAssociation{uuid.uuid4().hex}")

    assoc_id = sp.post_obj_tag(public_source.id, tag.id, group_ids=[public_group.id]).id

    sp.delete_obj_tag(assoc_id)

    with pytest.raises(SkyPortalError, match="Association not found") as err:
        sp.delete_obj_tag(assoc_id)
    assert err.value.status_code == 404
