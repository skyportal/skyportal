from playwright.sync_api import expect

import skyportal


def test_skyportal_version_displayed(page):
    page.goto("/about")
    expect(
        page.locator(f"//*[contains(.,'{skyportal.__version__}')]").first
    ).to_be_visible()
    page.locator("//button[contains(.,'Show BiBTeX')]").first.click()
    expect(
        page.locator("//*[contains(.,'Journal of Open Source Software')]").first
    ).to_be_visible()
    page.locator("//button[contains(.,'Hide BiBTeX')]").first.click()


def test_invalid_route(page):
    page.goto("/invalid_route")
    expect(page.locator("//*[contains(.,'Invalid route')]").first).to_be_visible()
