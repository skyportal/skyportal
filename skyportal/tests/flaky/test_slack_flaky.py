import pytest
from playwright.sync_api import expect


@pytest.mark.flaky(reruns=2)
def test_slack_url(page, user):
    good_path = "https://hooks.slack.com/"
    bad_path = "http://garbage.url"

    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    slack_toggle = page.locator('//*[@data-testid="slack_toggle"]').first
    expect(slack_toggle).to_be_visible()

    if not slack_toggle.is_checked():
        slack_toggle.click()

    expect(page.locator('//*[@data-testid="slack_url"]').first).to_be_visible()

    # bad URL -> validation error appears
    page.locator('//input[@name="url"]').first.fill(bad_path)
    page.locator('//input[@name="url"]').first.press("Enter")
    page.locator("//header").first.click()  # blur the field
    expect(page.locator('//*[text()="Must be a Slack URL"]').first).to_be_visible()

    # good URL -> error goes away
    page.locator('//input[@name="url"]').first.fill(good_path)
    page.locator('//input[@name="url"]').first.press("Enter")
    page.locator("//header").first.click()
    expect(page.locator('//*[text()="Must be a Slack URL"]').first).to_be_hidden()
