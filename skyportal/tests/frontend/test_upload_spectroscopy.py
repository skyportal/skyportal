import os
from selenium.webdriver import ActionChains
import uuid

import pytest
from skyportal.enum_types import ALLOWED_SPECTRUM_TYPES


@pytest.mark.flaky(reruns=3)
def test_upload_spectroscopy(
    driver, sedm, super_admin_user, public_source, super_admin_token
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_spectrum/{public_source.id}")

    filename = "ZTF20abucjsa_20200909_LT_v1.ascii"

    attachment_file = driver.wait_for_xpath('//input[@type="file"]')
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            filename,
        ),
    )

    driver.wait_for_xpath(f'//*[contains(., "{filename}")]')

    mjd_element = driver.wait_for_xpath('//*[@id="root_mjd"]')
    driver.scroll_to_element_and_click(mjd_element)
    mjd_element.send_keys('51232.0')

    # Click somewhere outside to remove focus from MJD input
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    instrument_id_element_xpath = '//*[@id="root_instrument_id"]'
    instrument_element = driver.wait_for_xpath(instrument_id_element_xpath)
    driver.scroll_to_element_and_click(instrument_element)

    sedm_element_xpath = f'//li[contains(text(), "{sedm.name}")]'
    driver.click_xpath(sedm_element_xpath, scroll_parent=True)

    # Click somewhere outside to remove focus from instrument input
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    type_element_xpath = '//*[@id="root_spectrum_type"]'
    type_element = driver.wait_for_xpath(type_element_xpath)
    driver.scroll_to_element_and_click(type_element)

    host_element_xpath = f'//li[contains(text(), "{ALLOWED_SPECTRUM_TYPES[-1]}")]'
    driver.click_xpath(host_element_xpath, scroll_parent=True)

    label_element = driver.wait_for_xpath('//*[@id="root_user_label"]')
    driver.scroll_to_element_and_click(label_element)
    user_defined_label = str(uuid.uuid4())
    label_element.send_keys(user_defined_label)

    preview_button_xpath = '//button[contains(.,"Preview")]'
    preview_button = driver.wait_for_xpath(preview_button_xpath)
    driver.scroll_to_element_and_click(preview_button)

    submit_button_xpath = '//button[contains(.,"Upload Spectrum")]'
    submit_button = driver.wait_for_xpath(submit_button_xpath)
    driver.scroll_to_element_and_click(submit_button)

    driver.wait_for_xpath('//*[contains(.,"successful")]', timeout=10)

    # Go to "Share data" page to look for the spectrum, since we can't easily
    #  look into the plot on the Source page.
    driver.get(f"/share_data/{public_source.id}")

    driver.wait_for_xpath(f'//*[contains(.,"{sedm.name}")]', 20)
    driver.wait_for_xpath(f'//*[contains(.,"{ALLOWED_SPECTRUM_TYPES[-1]}")]', 20)
    driver.wait_for_xpath(f'//*[contains(.,"{user_defined_label}")]', 20)
