import uuid

from playwright.sync_api import expect

from skyportal.tests import api


def _set_color(locator, value):
    locator.evaluate(
        "(el, value) => { el.value = value; "
        "el.dispatchEvent(new Event('change', { bubbles: true })); }",
        value,
    )


def test_access_with_permission(page, super_admin_user):
    """Users with 'Manage sources' permission can access tag management."""
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/tag_management")

    expect(
        page.locator('//*[@data-testid="tag-management-page"]').first
    ).to_be_visible()
    expect(page.locator('//*[@data-testid="create-tag-button"]').first).to_be_visible()


def test_create_new_tag(page, super_admin_user):
    """Test creating a new tag from the tag management page."""
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/tag_management")

    expect(
        page.locator('//*[@data-testid="tag-management-page"]').first
    ).to_be_visible()

    page.locator('//*[@data-testid="create-tag-button"]').first.click()
    expect(page.locator('//*[@data-testid="create-tag-dialog"]').first).to_be_visible()

    test_tag_name = f"TestTag{uuid.uuid4().hex}"
    page.locator('//*[@data-testid="create-tag-name-input"]').first.fill(test_tag_name)

    _set_color(
        page.locator('//*[@data-testid="create-tag-color-input"]').first, "#ff0000"
    )

    expect(
        page.locator('//*[@data-testid="create-tag-preview-chip"]').first
    ).to_contain_text(test_tag_name)

    page.locator('//*[@data-testid="create-tag-save-button"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Tag created successfully")]').first
    ).to_be_visible()
    expect(
        page.locator(f'//span[contains(text(), "{test_tag_name}")]').first
    ).to_be_visible()


def test_create_tag_validation_empty_name(page, super_admin_user):
    """Test validation when trying to create a tag with empty name."""
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/tag_management")

    expect(
        page.locator('//*[@data-testid="tag-management-page"]').first
    ).to_be_visible()

    page.locator('//*[@data-testid="create-tag-button"]').first.click()
    expect(page.locator('//*[@data-testid="create-tag-dialog"]').first).to_be_visible()

    page.locator('//*[@data-testid="create-tag-save-button"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Tag name cannot be empty")]').first
    ).to_be_visible()
    expect(page.locator('//*[@data-testid="create-tag-dialog"]').first).to_be_visible()


def test_edit_existing_tag(page, super_admin_user, super_admin_token):
    """Test editing an existing tag."""
    tag_name = f"EditableTag{uuid.uuid4().hex}"
    status, data = api(
        "POST",
        "objtagoption",
        data={"name": tag_name, "color": "#0000ff"},
        token=super_admin_token,
    )
    assert status == 200
    tag_id = data["data"]["id"]

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/tag_management")

    expect(
        page.locator('//*[@data-testid="tag-management-page"]').first
    ).to_be_visible()

    page.locator(f'//*[@data-testid="edit-tag-button-{tag_id}"]').first.click()
    expect(page.locator('//*[@data-testid="edit-tag-dialog"]').first).to_be_visible()

    test_tag_name = f"EditedTag{uuid.uuid4().hex}"
    page.locator('//*[@data-testid="edit-tag-name-input"]').first.fill(test_tag_name)

    _set_color(
        page.locator('//*[@data-testid="edit-tag-color-input"]').first, "#00ff00"
    )

    expect(
        page.locator('//*[@data-testid="edit-tag-preview-chip"]').first
    ).to_contain_text(test_tag_name)

    page.locator('//*[@data-testid="edit-tag-save-button"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Tag updated successfully")]').first
    ).to_be_visible()
    expect(
        page.locator(f'//span[contains(text(), "{test_tag_name}")]').first
    ).to_be_visible()


def test_delete_tag(page, super_admin_user, super_admin_token):
    """Test deleting a tag with confirmation dialog."""
    tag_name = f"DeleteableTag{uuid.uuid4().hex}"
    status, data = api(
        "POST",
        "objtagoption",
        data={"name": tag_name, "color": "#ff0000"},
        token=super_admin_token,
    )
    assert status == 200
    tag_id = data["data"]["id"]

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/tag_management")

    expect(
        page.locator('//*[@data-testid="tag-management-page"]').first
    ).to_be_visible()

    delete_button = page.locator(
        f'//*[@data-testid="delete-tag-button-{tag_id}"]'
    ).first

    # First, test cancelling the deletion
    delete_button.click()
    expect(page.locator('//*[@data-testid="delete-tag-dialog"]').first).to_be_visible()
    expect(page.locator('//*[@data-testid="delete-tag-title"]').first).to_contain_text(
        tag_name
    )
    expect(
        page.locator('//*[@data-testid="delete-tag-confirmation-text"]').first
    ).to_contain_text(tag_name)
    expect(
        page.locator('//*[@data-testid="delete-tag-warning-text"]').first
    ).to_contain_text("Warning")

    page.locator('//*[@data-testid="delete-tag-cancel-button"]').first.click()
    expect(page.locator('//*[@data-testid="delete-tag-dialog"]').first).to_be_hidden()
    expect(
        page.locator(f'//span[contains(text(), "{tag_name}")]').first
    ).to_be_visible()

    # Then, delete the tag
    delete_button.click()
    expect(page.locator('//*[@data-testid="delete-tag-dialog"]').first).to_be_visible()
    page.locator('//*[@data-testid="delete-tag-confirm-button"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Tag deleted successfully")]').first
    ).to_be_visible()
    expect(page.locator(f'//span[contains(text(), "{tag_name}")]').first).to_be_hidden()
