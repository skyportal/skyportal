import os
import uuid

import pytest
from selenium.webdriver.common.keys import Keys


@pytest.mark.flaky(reruns=2)
def test_upload_galaxies(driver, super_admin_user, super_admin_token):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/galaxies/")

    filename = "CLU_mini.csv"
    catalog_name = str(uuid.uuid4())

    submit_button_xpath = '//button[@name="new_gcnevent"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    driver.wait_for_xpath('//*[@id="root_catalogName"]').send_keys(catalog_name)
    attachment_file = driver.wait_for_xpath('//input[@type="file"]')
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            filename,
        ),
    )

    driver.wait_for_xpath(f'//*[contains(., "{filename}")]')
    submit_button_xpath = '//button[contains(.,"Submit")]'
    driver.click_xpath(submit_button_xpath, scroll_parent=True)

    # The galaxy name search is a server-side search box in the data grid
    # toolbar; type into it and press Enter to trigger the query.
    search_bar = driver.wait_for_xpath('//*[@data-testid="galaxy-search-input"]//input')
    search_bar.send_keys("6dFgs gJ0001313-055904")
    search_bar.send_keys(Keys.ENTER)
    driver.wait_for_xpath('//*[text()="6dFgs gJ0001313-055904"]', timeout=10)
    search_bar.clear()
