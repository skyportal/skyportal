from playwright.sync_api import expect


def test_foldable_sidebar(page):
    page.goto("/")

    # The sidebar text is always in the DOM; on desktop it starts minimized
    # (present but not visible) and toggles with the menu (hamburger) button.
    dashboard = page.locator('//p[contains(text(),"Dashboard")]').first
    hamburger = page.locator('//button[@aria-label="open drawer"]').first

    expect(dashboard).to_be_hidden()

    # Open the sidebar fully via the menu button.
    hamburger.click()
    expect(dashboard).to_be_visible()

    # Minimize it again.
    hamburger.click()
    expect(dashboard).to_be_hidden()

    original_viewport = page.viewport_size
    try:
        # Switch to a mobile viewport: the sidebar is fully hidden.
        page.set_viewport_size({"width": 400, "height": 800})
        expect(dashboard).to_be_hidden()

        # Open it fully via the menu button.
        hamburger.click()
        expect(dashboard).to_be_visible()
    finally:
        page.set_viewport_size(original_viewport)
