def test_fixed_location_filtering(  # noqa: E302
    driver, view_only_user, hst, public_source, keck1_telescope
):
    driver.get(f'/become_user/{view_only_user.id}')
    driver.get(f'/observability/{public_source.id}')
    driver.wait_for_xpath(f'//*[text()="{keck1_telescope.name}"]')
    driver.wait_for_xpath_to_disappear(f'//*[text()="{hst.name}"]')
    # Make sure a plot loads
    driver.wait_for_xpath("//canvas")


def test_user_preference_filtering(
    driver, view_only_user, public_source, keck1_telescope, p60_telescope
):
    driver.get(f'/become_user/{view_only_user.id}')
    driver.get(f'/observability/{public_source.id}')

    # Both show up by default
    driver.wait_for_xpath(f'//*[text()="{keck1_telescope.name}"]')
    driver.wait_for_xpath(f'//*[text()="{p60_telescope.name}"]')

    # Now go to preferences and set to only show p60
    driver.get("/profile")
    driver.click_xpath("//*[@data-testid='selectTelescopes']")
    driver.click_xpath(f"//*[@data-testid='telescope_{p60_telescope.id}']")

    # Now should only show p60
    driver.get(f'/observability/{public_source.id}')
    driver.wait_for_xpath_to_disappear(f'//*[text()="{keck1_telescope.name}"]')
    driver.wait_for_xpath(f'//*[text()="{p60_telescope.name}"]')
