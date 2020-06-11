import skyportal


def test_skyportal_version_displayed(driver):
    driver.get('/about')
    driver.wait_for_xpath(f"//*[contains(.,'{skyportal.__version__}')]")
