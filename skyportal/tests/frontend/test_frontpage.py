def test_foldable_sidebar(driver):
    driver.get('/')

    # on desktop, we should see a minimized sidebar only, meaning we can find the text
    # but it is not visible until we clicking the menu button
    dashboard = '//p[contains(text(),"Dashboard")]'
    sidebar_text = driver.wait_for_xpath(dashboard)
    assert not sidebar_text.is_displayed()

    # we open the sidebar fully by clicking the menu button
    hamburger = '//button[@aria-label="open drawer"]'
    driver.click_xpath(hamburger)
    driver.wait_for_xpath_to_appear(dashboard)

    # we minimize the sidebar by clicking the menu button again
    driver.click_xpath(hamburger)
    driver.wait_for_xpath_to_disappear(dashboard)

    current_window_size = driver.get_window_size()

    try:
        # we change the window size to mobile
        driver.set_window_size(400, 800)

        # the side bar should he hidden again, but this time fully
        # meaning we should not be able to find the sidebar text
        driver.wait_for_xpath_to_disappear(dashboard)

        # we open the sidebar fully by clicking the menu button
        driver.click_xpath(hamburger)
        sidebar_text = driver.wait_for_xpath(dashboard)
        assert sidebar_text.is_displayed()
    except Exception as e:
        raise e
    finally:
        driver.set_window_size(
            current_window_size['width'], current_window_size['height']
        )
