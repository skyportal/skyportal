import uuid

import pytest
from playwright.sync_api import expect


@pytest.mark.flaky(reruns=2)
def test_add_token(page, user):
    token_name = str(uuid.uuid4())
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    page.locator('//*[@data-testid="acls[0]"]').first.click()
    page.locator('//*[@data-testid="acls[1]"]').first.click()
    page.locator('//input[@name="name"]').first.fill(token_name)
    page.locator('//button[contains(.,"Generate Token")]').first.click()
    expect(
        page.locator(f'//div[@role="gridcell" and contains(.,"{token_name}")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_cannot_create_more_than_one_token(page, user, view_only_token):
    token_name = str(uuid.uuid4())
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    page.locator('//*[@data-testid="acls[0]"]').first.click()
    page.locator('//*[@data-testid="acls[1]"]').first.click()
    page.locator('//input[@name="name"]').first.fill(token_name)
    page.locator('//button[contains(.,"Generate Token")]').first.click()
    expect(
        page.locator(
            '//*[text()="You have reached the maximum number of tokens allowed for your account type."]'
        ).first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_delete_token(page, user, view_only_token):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    expect(page.locator(f'//input[@value="{view_only_token}"]').first).to_be_visible()
    page.locator('//button[contains(text(),"Delete")]').first.click()
    expect(page.locator(f'//input[@value="{view_only_token}"]').first).to_be_hidden()


@pytest.mark.flaky(reruns=2)
def test_add_duplicate_token_error_message(page, super_admin_user):
    token_name = str(uuid.uuid4())
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/profile")
    page.locator('//*[@data-testid="acls[0]"]').first.click()
    page.locator('//*[@data-testid="acls[1]"]').first.click()
    page.locator('//input[@name="name"]').first.fill(token_name)
    page.locator('//button[contains(.,"Generate Token")]').first.click()
    expect(
        page.locator(f'//div[@role="gridcell" and contains(.,"{token_name}")]').first
    ).to_be_visible()

    page.locator('//input[@name="name"]').first.fill(token_name)
    page.locator('//button[contains(.,"Generate Token")]').first.click()
    expect(
        page.locator('//div[contains(.,"Duplicate token name")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_sys_admin_can_create_multiple_tokens(page, super_admin_user):
    token_name = str(uuid.uuid4())
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/profile")
    page.locator('//*[@data-testid="acls[0]"]').first.click()
    page.locator('//*[@data-testid="acls[1]"]').first.click()
    page.locator('//input[@name="name"]').first.fill(token_name)
    page.locator('//button[contains(.,"Generate Token")]').first.click()
    expect(
        page.locator(f'//div[@role="gridcell" and contains(.,"{token_name}")]').first
    ).to_be_visible()

    token2_name = str(uuid.uuid4())
    page.locator('//*[@data-testid="acls[0]"]').first.click()
    page.locator('//input[@name="name"]').first.fill(token2_name)
    page.locator('//button[contains(.,"Generate Token")]').first.click()
    expect(
        page.locator(f'//div[@role="gridcell" and contains(.,"{token2_name}")]').first
    ).to_be_visible()
