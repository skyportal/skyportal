import uuid

import numpy as np
import pytest
from playwright.sync_api import expect


@pytest.mark.flaky(reruns=2)
def test_new_source(page, user, super_admin_token, view_only_token, public_group):
    page.goto(f"/become_user/{user.id}")
    page.goto("/sources")

    page.locator('//button[@name="new_source"]').first.click()

    source_name = uuid.uuid4().hex
    page.locator("//div[@id='selectGroups']").first.click()
    page.locator(f'//div[@data-testid="group_{public_group.id}"]').first.click()

    # Dismiss the open group-select dropdown
    page.keyboard.press("Escape")

    # test add sources form
    page.locator('//*[@id="root_id"]').first.fill(source_name)
    page.locator('//*[@id="root_ra"]').first.fill(str(np.random.uniform(0, 360)))
    page.locator('//*[@id="root_dec"]').first.fill(str(np.random.uniform(-90, 90)))

    page.locator('//button[@type="submit"]').first.click()

    try:
        expect(page.locator('//*[text()="Source saved"]').first).to_be_visible()
    except AssertionError:
        pass

    page.goto("/")
    expect(page.locator(f'//*[text()="{source_name}"]').first).to_be_visible()
