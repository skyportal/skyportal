def test_foldable_sidebar(driver):
    driver.get('/')
    dashboard = '//span[contains(text(),"Dashboard")]'
    sidebar_text = driver.wait_for_xpath(dashboard)
    assert sidebar_text.is_displayed()

    hamburger = '//button[@aria-label="open drawer"]'
    driver.click_xpath(hamburger)

    driver.wait_for_xpath_to_disappear(dashboard)

    driver.click_xpath(hamburger)
    driver.wait_for_xpath_to_appear(dashboard)
