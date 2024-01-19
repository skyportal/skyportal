import os
import uuid
import pytest


@pytest.mark.flaky(reruns=2)
def test_upload_galaxies(driver, super_admin_user, super_admin_token):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/galaxies/")

    filename = "CLU_mini.csv"
    catalog_name = str(uuid.uuid4())

    driver.wait_for_xpath('//*[@id="root_catalogName"]').send_keys(catalog_name)
    attachment_file = driver.wait_for_xpath('//input[@type="file"]')
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            filename,
        ),
    )

    driver.wait_for_xpath(f'//*[contains(., "{filename}")]')
    submit_button_xpath = '//button[contains(.,"Submit")]'
    driver.click_xpath(submit_button_xpath, scroll_parent=True)

    search_button_xpath = '//button[@data-testid="Search-iconButton"]'
    driver.click_xpath(search_button_xpath, scroll_parent=True)
    search_bar = driver.wait_for_xpath('//input[@aria-label="Search"]')
    search_bar.send_keys('6dFgs gJ0001313-055904')
    driver.wait_for_xpath('//*[text()="6dFgs gJ0001313-055904"]', timeout=10)
    search_bar.clear()
