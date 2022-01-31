from skyportal.tests import api
from selenium.webdriver.common.keys import Keys

import pytest


@pytest.mark.flaky(reruns=3)
def test_super_user_post_shift(
    public_group, super_admin_token, super_admin_user, driver
):

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/shifts")

    request_data = {
        'group_id': public_group.id,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
    }

    status, data = api('POST', 'shift', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'shift/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # check for API shift
    driver.wait_for_xpath(
        f'//span[text()[contains(.,"{public_group.name}")]]', timeout=20
    )

    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01/01/2022')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('P')

    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('03/01/2022')
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('P')

    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('02/01/2022 01:01:10')
    driver.click_xpath('//*[@id="root_group_id"]')
    driver.click_xpath('//li[contains(text(), "Sitewide Group")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for dropdown shift
    driver.wait_for_xpath('//span[text()[contains(.,"Sitewide Group")]]')
