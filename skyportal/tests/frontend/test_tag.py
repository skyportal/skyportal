import uuid

import pytest
from selenium.webdriver.common.by import By

from skyportal.tests import api


def test_add_delete_tag(driver, public_source, super_admin_token, super_admin_user):
    """Test the basic CRUD operations for object tags."""

    driver.get(f"/become_user/{super_admin_user.id}")
    tag_name = f"testtag{uuid.uuid4().hex}"
    status, data = api(
        "POST",
        "objtagoption",
        data={"name": tag_name},
        token=super_admin_token,
    )
    assert status == 200

    tag_id = data["data"]["id"]

    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[contains(text(), "{public_source.id}")]', timeout=20)

    add_tag_button = driver.wait_for_xpath_to_be_clickable(
        '*//button[@data-testid="add-tag-button"]',
        timeout=10,
    )
    add_tag_button.click()
    driver.wait_for_xpath('//div[@data-testid="add-tag-dialog"]', timeout=20)

    autocomplete = driver.wait_for_xpath_to_be_clickable(
        '//div[@data-testid="tag-select"]'
    )
    autocomplete.click()

    driver.wait_for_xpath(
        '//div[contains(@class, "MuiAutocomplete-popper")]', timeout=10
    )

    option = driver.wait_for_xpath_to_be_clickable(
        f'//li[contains(text(), "{tag_name}")]', timeout=10
    )
    option.click()

    driver.wait_for_xpath_to_be_clickable('//button[@data-testid="save-tag-button"]')
    driver.click_xpath('//button[@data-testid="save-tag-button"]')
    driver.wait_for_xpath('//*[contains(text(), "Tag added successfully")]', timeout=10)

    driver.wait_for_xpath(f'//span[contains(text(), "{tag_name}")]')

    driver.click_xpath(
        f"//*[@data-testid='tag-chip-{tag_id}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )
    driver.wait_for_xpath('//*[contains(text(), "Source Tag deleted")]', timeout=10)
    driver.wait_for_xpath_to_disappear(f"//div[@data-testid='tag-chip-{tag_id}']")


def test_create_new_tag(driver, user, public_source, super_admin_user):
    """Test creating a new tag from the source page."""

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")

    driver.wait_for_xpath(f'//h6[contains(text(), "{public_source.id}")]', timeout=20)

    add_tag_button = driver.wait_for_xpath_to_be_clickable(
        '*//button[@data-testid="add-tag-button"]',
        timeout=10,
    )
    add_tag_button.click()

    driver.wait_for_xpath('//div[@data-testid="add-tag-dialog"]', timeout=20)

    tag_name = f"newtag{uuid.uuid4().hex}"
    tag_input = driver.wait_for_xpath('//input[@data-testid="new-tag-input"]')
    tag_input.send_keys(tag_name)
    driver.wait_for_xpath('//button[@data-testid="create-tag-button"]')
    driver.click_xpath('//button[@data-testid="create-tag-button"]')
    driver.wait_for_xpath('//*[contains(text(), "Tag created successfully")]')

    driver.wait_for_xpath('//button[@data-testid="save-tag-button"]')
    driver.click_xpath('//button[@data-testid="save-tag-button"]')

    driver.wait_for_xpath(f'//span[contains(text(), "{tag_name}")]')


def test_permission_for_tag_creation(driver, user, public_source):
    """Test that normal users can't create tags (only admins or users with permission)."""
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")

    driver.wait_for_xpath(f'//h6[contains(text(), "{public_source.id}")]', timeout=20)

    add_tag_button = driver.wait_for_xpath_to_be_clickable(
        '*//button[@data-testid="add-tag-button"]',
        timeout=10,
    )
    add_tag_button.click()

    driver.wait_for_xpath('//div[@data-testid="add-tag-dialog"]', timeout=20)

    create_section_elements = driver.find_elements(
        By.XPATH, '//div[contains(@class, "createTagSection")]'
    )
    assert not create_section_elements
    driver.wait_for_xpath('//button[contains(text(), "Cancel")]')
    driver.click_xpath('//button[contains(text(), "Cancel")]')
