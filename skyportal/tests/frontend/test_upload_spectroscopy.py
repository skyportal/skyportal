import os
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
    mjd_element.send_keys('51232.')

    instrument_id_element_xpath = '//*[@id="root_instrument_id"]'
    driver.click_xpath(instrument_id_element_xpath, scroll_parent=True)

    sedm_element_xpath = f'//li[contains(text(), "{sedm.name}")]'
    driver.click_xpath(sedm_element_xpath, scroll_parent=True)

    type_element_xpath = '//*[@id="root_spectrum_type"]'
    driver.click_xpath(type_element_xpath, scroll_parent=True)

    host_element_xpath = f'//li[contains(text(), "{ALLOWED_SPECTRUM_TYPES[-1]}")]'
    driver.click_xpath(host_element_xpath, scroll_parent=True)

    label_element = driver.wait_for_xpath('//*[@id="root_user_label"]')
    driver.scroll_to_element_and_click(label_element)
    user_defined_label = str(uuid.uuid4())
    label_element.send_keys(user_defined_label)

    preview_button_xpath = '//button[contains(.,"Preview")]'
    driver.click_xpath(preview_button_xpath, scroll_parent=True)

    submit_button_xpath = '//button[contains(.,"Upload Spectrum")]'
    driver.click_xpath(submit_button_xpath, scroll_parent=True, timeout=30)

    driver.wait_for_xpath('//*[contains(.,"successful")]')

    # Go to "Share data" page to look for the spectrum, since we can't easily
    #  look into the Bokeh <canvas> tag on the Source page.
    driver.get(f"/share_data/{public_source.id}")

    driver.wait_for_xpath(f'//*[contains(.,"{sedm.name}")]', 20)
    driver.wait_for_xpath(f'//*[contains(.,"{ALLOWED_SPECTRUM_TYPES[-1]}")]', 20)
    driver.wait_for_xpath(f'//*[contains(.,"{user_defined_label}")]', 20)
