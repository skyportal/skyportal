def test_fixed_location_filtering(  # noqa: E302
    driver, view_only_user, hst, public_source, keck1_telescope
):
    driver.get(f"/become_user/{view_only_user.id}")
    driver.get(f"/observability/{public_source.id}")
    driver.click_xpath("//*[@id='selectTelescopes']")
    driver.wait_for_xpath(f'//*[text()="{keck1_telescope.name}"]')
    driver.wait_for_xpath_to_disappear(f'//*[text()="{hst.name}"]')


def test_user_preference_filtering(
    driver, view_only_user, public_source, keck1_telescope, p60_telescope
):
    driver.get(f"/become_user/{view_only_user.id}")
    driver.get(f"/observability/{public_source.id}")

    # Go to preferences and set to only show p60
    driver.get("/profile")
    driver.click_xpath("//*[@id='selectTelescopes']")
    driver.click_xpath(f"//li[@data-value='{p60_telescope.name}']")

    # Now should only show p60
    driver.get(f"/observability/{public_source.id}")
    driver.wait_for_xpath_to_disappear(f'//*[text()="{keck1_telescope.name}"]')
    driver.wait_for_xpath(f'//*[text()="{p60_telescope.name}"]')
