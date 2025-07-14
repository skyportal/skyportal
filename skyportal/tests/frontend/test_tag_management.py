import uuid

from skyportal.tests import api


def test_access_with_permission(driver, super_admin_user):
    """Test that users with 'Manage sources' permission can access tag management."""

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/tag_management")

    driver.wait_for_xpath('//*[@data-testid="tag-management-page"]', timeout=10)

    create_button = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="create-tag-button"]',
        timeout=10,
    )
    assert create_button is not None


def test_create_new_tag(driver, super_admin_user):
    """Test creating a new tag through the UI."""

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/tag_management")

    driver.wait_for_xpath('//*[@data-testid="tag-management-page"]', timeout=10)

    create_button = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="create-tag-button"]',
        timeout=10,
    )
    create_button.click()

    driver.wait_for_xpath('//*[@data-testid="create-tag-dialog"]')

    tag_name_field = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="create-tag-name-input"]',
        timeout=10,
    )
    test_tag_name = f"TestTag{uuid.uuid4().hex}"
    tag_name_field.clear()
    tag_name_field.send_keys(test_tag_name)

    color_picker = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="create-tag-color-input"]',
        timeout=10,
    )

    driver.execute_script("arguments[0].value = '#ff0000'", color_picker)
    driver.execute_script(
        "arguments[0].dispatchEvent(new Event('change'))", color_picker
    )

    preview_chip = driver.wait_for_xpath('//*[@data-testid="create-tag-preview-chip"]')
    assert preview_chip is not None
    assert test_tag_name in preview_chip.text

    create_save_button = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="create-tag-save-button"]',
        timeout=10,
    )
    create_save_button.click()

    driver.wait_for_xpath(
        '//*[contains(text(), "Tag created successfully")]', timeout=10
    )

    tag_in_table = driver.wait_for_xpath(
        f'//span[contains(text(), "{test_tag_name}")]',
        timeout=10,
    )
    assert tag_in_table is not None


def test_create_tag_validation_empty_name(driver, super_admin_user):
    """Test validation when trying to create a tag with empty name."""

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/tag_management")

    driver.wait_for_xpath('//*[@data-testid="tag-management-page"]', timeout=10)

    create_button = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="create-tag-button"]',
        timeout=10,
    )
    create_button.click()

    driver.wait_for_xpath('//*[@data-testid="create-tag-dialog"]')

    create_save_button = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="create-tag-save-button"]',
        timeout=10,
    )
    create_save_button.click()

    driver.wait_for_xpath(
        '//*[contains(text(), "Tag name cannot be empty")]', timeout=5
    )

    dialog_still_open = driver.wait_for_xpath(
        '//*[@data-testid="create-tag-dialog"]', timeout=3
    )
    assert dialog_still_open is not None


def test_edit_existing_tag(driver, super_admin_user, super_admin_token):
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

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/tag_management")

    driver.wait_for_xpath('//*[@data-testid="tag-management-page"]', timeout=10)

    edit_button = driver.wait_for_xpath_to_be_clickable(
        f'//*[@data-testid="edit-tag-button-{tag_id}"]',
        timeout=10,
    )
    edit_button.click()

    driver.wait_for_xpath('//*[@data-testid="edit-tag-dialog"]')

    tag_name_field = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="edit-tag-name-input"]',
        timeout=10,
    )
    test_tag_name = f"EditedTag{uuid.uuid4().hex}"
    tag_name_field.clear()
    tag_name_field.send_keys(test_tag_name)

    color_picker = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="edit-tag-color-input"]',
        timeout=10,
    )
    driver.execute_script("arguments[0].value = '#00ff00'", color_picker)
    driver.execute_script(
        "arguments[0].dispatchEvent(new Event('change'))", color_picker
    )

    preview_chip = driver.wait_for_xpath('//*[@data-testid="edit-tag-preview-chip"]')
    assert preview_chip is not None
    assert test_tag_name in preview_chip.text

    save_button = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="edit-tag-save-button"]',
        timeout=10,
    )
    save_button.click()

    driver.wait_for_xpath(
        '//*[contains(text(), "Tag updated successfully")]', timeout=10
    )

    updated_tag = driver.wait_for_xpath(
        f'//span[contains(text(), "{test_tag_name}")]',
        timeout=10,
    )
    assert updated_tag is not None


def test_delete_tag(driver, super_admin_user, super_admin_token):
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

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/tag_management")

    driver.wait_for_xpath('//*[@data-testid="tag-management-page"]', timeout=10)

    delete_button = driver.wait_for_xpath_to_be_clickable(
        f'//*[@data-testid="delete-tag-button-{tag_id}"]',
        timeout=10,
    )
    delete_button.click()

    # First, test to cancel the deletion
    driver.wait_for_xpath('//*[@data-testid="delete-tag-dialog"]')

    title_element = driver.wait_for_xpath('//*[@data-testid="delete-tag-title"]')
    assert tag_name in title_element.text

    confirmation_text = driver.wait_for_xpath(
        '//*[@data-testid="delete-tag-confirmation-text"]'
    )
    assert tag_name in confirmation_text.text

    warning_text = driver.wait_for_xpath('//*[@data-testid="delete-tag-warning-text"]')
    assert "Warning" in warning_text.text

    cancel_button = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="delete-tag-cancel-button"]',
        timeout=10,
    )
    cancel_button.click()
    driver.wait_for_xpath_to_disappear('//*[@data-testid="delete-tag-dialog"]')

    tag_still_there = driver.wait_for_xpath(
        f'//span[contains(text(), "{tag_name}")]',
        timeout=10,
    )
    assert tag_still_there is not None

    # Then, delete the tag
    delete_button.click()

    driver.wait_for_xpath('//*[@data-testid="delete-tag-dialog"]')
    confirm_delete_button = driver.wait_for_xpath_to_be_clickable(
        '//*[@data-testid="delete-tag-confirm-button"]',
        timeout=10,
    )
    confirm_delete_button.click()

    driver.wait_for_xpath(
        '//*[contains(text(), "Tag deleted successfully")]', timeout=10
    )

    driver.wait_for_xpath_to_disappear(
        f'//span[contains(text(), "{tag_name}")]',
        timeout=3,
    )
