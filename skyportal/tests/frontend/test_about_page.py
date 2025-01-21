import skyportal


def test_skyportal_version_displayed(driver):
    driver.get("/about")
    driver.wait_for_xpath(f"//*[contains(.,'{skyportal.__version__}')]")
    driver.click_xpath("//button[contains(.,'Show BiBTeX')]")
    driver.wait_for_xpath("//*[contains(.,'Journal of Open Source Software')]")
    driver.click_xpath("//button[contains(.,'Hide BiBTeX')]")


def test_invalid_route(driver):
    driver.get("/invalid_route")
    driver.wait_for_xpath("//*[contains(.,'Invalid route')]")
