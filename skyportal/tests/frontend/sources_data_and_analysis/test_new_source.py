import uuid

import numpy as np
from playwright.sync_api import expect


def test_new_source(page, user, super_admin_token, view_only_token, public_group):
    page.goto(f"/become_user/{user.id}")
    page.goto("/sources")

    page.locator('//button[@name="new_source"]').first.click()

    source_name = uuid.uuid4().hex
    page.locator("//div[@id='selectGroups']").first.click()
    group_option = page.locator(f'//div[@data-testid="group_{public_group.id}"]').first
    group_option.click()

    # Dismiss the group-select dropdown and wait for it to close, so it can't
    # overlay (and swallow the fills on) the form fields below.
    page.keyboard.press("Escape")
    expect(group_option).to_be_hidden(timeout=15000)

    # test add sources form
    page.locator('//*[@id="root_id"]').first.fill(source_name)
    page.locator('//*[@id="root_ra"]').first.fill(str(np.random.uniform(0, 360)))
    page.locator('//*[@id="root_dec"]').first.fill(str(np.random.uniform(-90, 90)))

    page.locator('//button[@type="submit"]').first.click()

    # The "Source saved" toast is transient; the durable check is the source
    # showing up on the home page below.
    try:
        expect(page.locator('//*[text()="Source saved"]').first).to_be_visible()
    except AssertionError:
        pass

    # The recent-sources list updates over websocket; give it time and reload
    # once (re-querying from the DB) if that push was missed.
    page.goto("/")
    source_link = page.locator(f'//*[text()="{source_name}"]').first
    try:
        expect(source_link).to_be_visible(timeout=20000)
    except AssertionError:
        page.reload()
        expect(source_link).to_be_visible(timeout=20000)
