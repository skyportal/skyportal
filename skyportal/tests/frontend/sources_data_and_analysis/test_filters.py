import uuid

import pytest
from playwright.sync_api import expect


@pytest.mark.flaky(reruns=2)
def test_add_filter(page, super_admin_user, public_group):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    page.get_by_role("tab", name="All Groups").click()
    page.locator(f'//div[@data-id="{public_group.id}"]').first.click()
    page.get_by_role("tab", name="Streams and filters").click()

    filter_name = str(uuid.uuid4())
    page.get_by_role("button", name="add filter").first.click()
    page.locator('//input[@name="filter_name"]').first.fill(filter_name)
    page.locator('//button[@type="submit"]').first.click()
    expect(page.locator(f'//span[contains(.,"{filter_name}")]')).to_have_count(1)

    # go to filter page
    page.locator(f'//span[contains(.,"{filter_name}")]').first.click()
    expect(page.locator(f'//h6[contains(.,"{filter_name}")]').first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_rename_filter(page, super_admin_user, public_group, public_filter):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/group/{public_group.id}")
    page.get_by_role("tab", name="Streams and filters").click()

    page.locator(f'//*[@data-testid="rename-filter-{public_filter.id}"]').first.click()
    new_name = str(uuid.uuid4())
    page.locator('//input[@data-testid="filter-name-input"]').first.fill(new_name)
    page.locator('//*[@data-testid="save-filter-name-button"]').first.click()
    expect(page.locator(f'//span[contains(.,"{new_name}")]')).to_have_count(1)
