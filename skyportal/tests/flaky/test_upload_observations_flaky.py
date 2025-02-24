import os

import pytest

from skyportal.tests.external.test_moving_objects import add_telescope_and_instrument


@pytest.mark.flaky(reruns=2)
def test_upload_observations(driver, super_admin_user, super_admin_token):
    add_telescope_and_instrument("ZTF", super_admin_token, list(range(5)))

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/observations/")

    filename = "sample_observation_data_upload_malformed.csv"

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

    filename = "sample_observation_data_upload.csv"

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

    search_button_xpath = '//button[@data-testid="Search-iconButton"]'
    driver.click_xpath(search_button_xpath, scroll_parent=True)
    search_bar = driver.wait_for_xpath('//input[@aria-label="Search"]')
    search_bar.send_keys("84434604")
    driver.wait_for_xpath('//*[text()="84434604"]', timeout=10)
