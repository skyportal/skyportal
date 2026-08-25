import uuid

from playwright.sync_api import expect

from skyportal.tests import api


def test_add_delete_tag(page, public_source, super_admin_token, super_admin_user):
    """Test the basic CRUD operations for object tags."""
    page.goto(f"/become_user/{super_admin_user.id}")
    tag_name = f"testtag{uuid.uuid4().hex}"
    status, data = api(
        "POST", "objtagoption", data={"name": tag_name}, token=super_admin_token
    )
    assert status == 200

    page.goto(f"/source/{public_source.id}")
    expect(
        page.locator(f'//h6[contains(text(), "{public_source.id}")]').first
    ).to_be_visible()

    page.locator('//button[@data-testid="add-tag-button"]').first.click()
    expect(page.locator('//div[@data-testid="add-tag-dialog"]').first).to_be_visible()

    page.locator('//div[@data-testid="tag-select"]').first.click()
    expect(
        page.locator('//div[contains(@class, "MuiAutocomplete-popper")]').first
    ).to_be_visible()
    page.locator(
        f'//li//span[contains(@class, "MuiChip-label") and contains(text(), "{tag_name}")]'
    ).first.click()

    page.locator('//button[@data-testid="save-tag-button"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Tag added successfully")]').first
    ).to_be_visible()
    expect(
        page.locator(f'//span[contains(text(), "{tag_name}")]').first
    ).to_be_visible()

    page.locator(
        f"//div[contains(@class,'MuiChip-root') and .//span[contains(text(),'{tag_name}')]]//*[contains(@class,'MuiChip-deleteIcon')]"
    ).first.click()
    page.locator('//*[@data-testid="delete-tag-button"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Tag removed from source")]').first
    ).to_be_visible()
    expect(
        page.locator(
            f"//div[contains(@class,'MuiChip-root') and .//span[contains(text(),'{tag_name}')]]"
        ).first
    ).to_be_hidden()


def test_create_new_tag(page, user, public_source, super_admin_user):
    """Test creating a new tag from the source page."""
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(
        page.locator(f'//h6[contains(text(), "{public_source.id}")]').first
    ).to_be_visible()

    page.locator('//button[@data-testid="add-tag-button"]').first.click()
    expect(page.locator('//div[@data-testid="add-tag-dialog"]').first).to_be_visible()

    tag_name = f"newtag{uuid.uuid4().hex}"
    page.locator('//input[@data-testid="new-tag-input"]').first.fill(tag_name)
    page.locator('//button[@data-testid="create-tag-button"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Tag created successfully")]').first
    ).to_be_visible()

    page.locator('//button[@data-testid="save-tag-button"]').first.click()
    expect(
        page.locator(f'//span[contains(text(), "{tag_name}")]').first
    ).to_be_visible()


def test_permission_for_tag_creation(page, user, public_source):
    """Normal users can't create tags (only admins or users with permission)."""
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(
        page.locator(f'//h6[contains(text(), "{public_source.id}")]').first
    ).to_be_visible()

    page.locator('//button[@data-testid="add-tag-button"]').first.click()
    expect(page.locator('//div[@data-testid="add-tag-dialog"]').first).to_be_visible()

    expect(page.locator('//div[contains(@class, "createTagSection")]')).to_have_count(0)
    page.locator('//button[contains(text(), "Cancel")]').first.click()
