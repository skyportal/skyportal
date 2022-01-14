from skyportal.tests import api
from selenium.webdriver.common.keys import Keys

import uuid


def test_super_user_post_allocation(
    public_group, super_admin_token, super_admin_user, driver
):

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/allocations")

    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': name,
            'nickname': name,
            'lat': 0.0,
            'lon': 0.0,
            'elevation': 0.0,
            'diameter': 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    instrument_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name,
            'type': 'imager',
            'band': 'NIR',
            'filters': ['f110w'],
            'telescope_id': telescope_id,
            'api_classname': 'ZTFAPI',
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    instrument_name2 = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name2,
            'type': 'imager',
            'band': 'NIR',
            'filters': ['f110w'],
            'telescope_id': telescope_id,
            'api_classname': 'ZTFAPI',
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    request_data = {
        'group_id': public_group.id,
        'instrument_id': instrument_id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'allocation/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # check for API instrument
    driver.wait_for_xpath(f'//span[text()="{instrument_name}/{name}"]', timeout=20)

    driver.wait_for_xpath('//*[@id="root_pi"]').send_keys('Shri')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01/01/2022')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('P')

    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('03/01/2022')
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('P')

    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('02/01/2022 01:01:10')
    driver.wait_for_xpath('//*[@id="root_hours_allocated"]').send_keys('100')
    driver.click_xpath('//*[@id="root_instrument_id"]')
    driver.click_xpath(f'//li[contains(text(), "{instrument_name2}")]')
    driver.click_xpath('//*[@id="root_group_id"]')
    driver.click_xpath('//li[contains(text(), "Sitewide Group")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    import pdb

    pdb.set_trace()

    # check for dropdown instrument
    driver.wait_for_xpath(f'//span[text()="{instrument_name2}/{name}"]')
