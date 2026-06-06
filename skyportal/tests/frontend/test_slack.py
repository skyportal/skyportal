import pytest
from playwright.sync_api import expect


def _set_url(url_input, value):
    # The URL field is an uncontrolled rjsf/MUI TextField whose onChange drives
    # the validation state; a plain fill() doesn't fire React's onChange, so the
    # state never updates. Type it so each keystroke dispatches an input event.
    url_input.click()
    url_input.press("ControlOrMeta+a")
    url_input.press("Delete")
    url_input.press_sequentially(value)


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


@pytest.mark.flaky(reruns=2)
def test_slack_url(page, user):
    good_path = "https://hooks.slack.com/"
    bad_path = "http://garbage.url"

    page.goto(f"/become_user/{user.id}")
    # The URL validation compares against the slack preamble from /api/config
    # (redux). Wait for that fetch so the validation doesn't read an undefined
    # preamble (which makes every URL fail) while config is still hydrating.
    with page.expect_response(lambda r: r.url.endswith("/api/config")):
        page.goto("/profile")
    slack_toggle = page.locator('//*[@data-testid="slack_toggle"]').first
    expect(slack_toggle).to_be_visible()

    if not slack_toggle.is_checked():
        slack_toggle.click()

    url_input = page.locator('//input[@name="url"]').first
    expect(page.locator('//*[@data-testid="slack_url"]').first).to_be_visible()

    # bad URL -> validation error appears
    _set_url(url_input, bad_path)
    page.locator("//header").first.click()  # blur the field
    expect(page.locator('//*[text()="Must be a Slack URL"]').first).to_be_visible()

    # good URL -> error goes away
    _set_url(url_input, good_path)
    page.locator("//header").first.click()
    expect(page.locator('//*[text()="Must be a Slack URL"]').first).to_be_hidden()
