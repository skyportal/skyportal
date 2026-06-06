import pytest
from playwright.sync_api import expect


@pytest.mark.flaky(reruns=2)
def test_slack_integration(page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    slack_toggle = page.locator('[data-testid="slack_toggle"]').first
    expect(slack_toggle).to_be_visible()

    if not slack_toggle.is_checked():
        slack_toggle.click()

    # uncheck the integration toggle
    slack_toggle.click()
