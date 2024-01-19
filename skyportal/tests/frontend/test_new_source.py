import uuid
from selenium.webdriver import ActionChains

import pytest
import numpy as np
from selenium.common.exceptions import TimeoutException


@pytest.mark.flaky(reruns=2)
def test_new_source(driver, user, super_admin_token, view_only_token, public_group):
    driver.get(f'/become_user/{user.id}')
    driver.get('/')

    driver.wait_for_xpath('//*[text()="Add a Source"]')
    driver.click_xpath('//*[text()="Add a Source"]')

    source_name = uuid.uuid4().hex
    driver.click_xpath("//div[@id='selectGroups']", scroll_parent=True)
    driver.click_xpath(
        f'//div[@data-testid="group_{public_group.id}"]',
        scroll_parent=True,
    )

    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # test add sources form
    driver.wait_for_xpath('//*[@id="root_id"]').send_keys(source_name)
    driver.wait_for_xpath('//*[@id="root_ra"]').send_keys(np.random.uniform(0, 360))
    driver.wait_for_xpath('//*[@id="root_dec"]').send_keys(np.random.uniform(-90, 90))

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    try:
        driver.wait_for_xpath('//*[text()="Source saved"]')
    except TimeoutException:
        pass

    driver.get('/')
    driver.wait_for_xpath(f'//*[text()="{source_name}"]')
