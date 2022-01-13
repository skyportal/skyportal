from skyportal.tests import api

import uuid


def test_instrument_frontend(super_admin_token, super_admin_user, driver):

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/instruments")

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

    driver.refresh()

    # check for API instrument
    driver.wait_for_xpath(f'//span[text()="{instrument_name}/{name}"]')

    # add dropdown instrument
    instrument_name2 = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(instrument_name2)
    driver.click_xpath('//*[@id="root_type"]')
    driver.click_xpath('//li[contains(text(), "Imager")]')
    driver.wait_for_xpath('//*[@id="root_band"]').send_keys('Optical')
    driver.click_xpath('//*[@id="root_api_classname"]')
    driver.click_xpath('//li[contains(text(), "ZTFAPI")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    driver.refresh()

    # check for dropdown instrument
    # driver.wait_for_xpath(f'//span[text()="{instrument_name2}/{name}"]')

    # try adding a second time
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(instrument_name2)
    driver.click_xpath('//*[@id="root_type"]')
    driver.click_xpath('//li[contains(text(), "Imager")]')
    driver.wait_for_xpath('//*[@id="root_band"]').send_keys('Optical')
    driver.click_xpath('//*[@id="root_api_classname"]')
    driver.click_xpath('//li[contains(text(), "ZTFAPI")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    driver.wait_for_xpath(
        '//span[text()="name: Instrument name matches another, please change."]'
    )
