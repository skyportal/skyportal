import uuid
import numpy as np
import pytest


@pytest.mark.flaky(reruns=2)
def test_new_source(
    driver, user, super_admin_token, upload_data_token, view_only_token, ztf_camera
):

    driver.get(f'/become_user/{user.id}')
    driver.get('/')

    driver.wait_for_xpath('//*[text()="Add a Source"]')

    # test add sources form
    driver.wait_for_xpath('//*[@id="root_id"]').send_keys(str(uuid.uuid4()))
    driver.wait_for_xpath('//*[@id="root_ra"]').send_keys(np.random.rand() * 360)
    driver.wait_for_xpath('//*[@id="root_dec"]').send_keys(np.random.rand() * 180 - 90)

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    driver.wait_for_xpath('//*[text()="Source saved"]')
