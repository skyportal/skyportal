from playwright.sync_api import expect


def test_fixed_location_filtering(
    page, view_only_user, hst, public_source, keck1_telescope
):
    page.goto(f"/become_user/{view_only_user.id}")
    page.goto(f"/observability/{public_source.id}")
    page.locator("//*[@id='selectTelescopes']").first.click()
    expect(page.locator(f'//*[text()="{keck1_telescope.name}"]').first).to_be_visible()
    expect(page.locator(f'//*[text()="{hst.name}"]').first).to_be_hidden()


def test_user_preference_filtering(
    page, view_only_user, public_source, keck1_telescope, p60_telescope
):
    page.goto(f"/become_user/{view_only_user.id}")
    page.goto(f"/observability/{public_source.id}")

    # Go to preferences and set to only show p60
    page.goto("/profile")
    page.locator("//*[@id='selectTelescopes']").first.click()
    page.locator(f"//li[@data-value='{p60_telescope.name}']").first.click()

    # Now should only show p60
    page.goto(f"/observability/{public_source.id}")
    expect(page.locator(f'//*[text()="{keck1_telescope.name}"]').first).to_be_hidden()
    expect(page.locator(f'//*[text()="{p60_telescope.name}"]').first).to_be_visible()
