import skyportal


def test_skyportal_version_displayed(driver):
    driver.get('/skyportal_info')
    driver.wait_for_xpath(f"//*[contains(.,'SkyPortal v{skyportal.__version__}')]")
