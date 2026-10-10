import pytest
from playwright.sync_api import expect

from skyportal.tests import open_preferences_panel


@pytest.mark.flaky(reruns=2)
def test_slack_connection(page, user):
    good_url = "https://hooks.slack.com/services/T000/B000/test"

    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    open_preferences_panel(page, "notifications")

    page.locator('[data-testid="slack_connect_button"]').first.click()
    url_input = page.locator('[data-testid="slack_input"]').first
    save = page.locator('[data-testid="slack_save_button"]').first

    url_input.fill("http://garbage.url")
    save.click()
    expect(page.locator('//*[text()="Must be a Slack URL"]').first).to_be_visible()

    url_input.fill(good_url)
    save.click()
    expect(page.locator(f'//*[text()="{good_url}"]').first).to_be_visible()

    page.locator('[data-testid="slack_disconnect_button"]').first.click()
    expect(page.locator('//*[text()="Not connected"]').first).to_be_visible()
