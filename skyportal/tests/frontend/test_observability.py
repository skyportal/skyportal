def test_space_based_filtering(  # noqa: E302
    driver, view_only_user, hst, public_source, keck1_telescope
):
    driver.get(f'/become_user/{view_only_user.id}')
    driver.get(f'/observability/{public_source.id}')
    driver.wait_for_xpath(f'//*[text()="{keck1_telescope.name}"]')
    driver.wait_for_xpath_to_disappear(f'//*[text()="{hst.name}"]')
