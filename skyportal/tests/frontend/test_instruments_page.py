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
    table = driver.wait_for_xpath('//*[contains(@class, "MuiList-root")]')
    findinst = False
    for row in table.find_elements_by_xpath(
        '//*[contains(@class, "MuiTypography-root")]'
    ):
        print(row.text, f"{instrument_name}/{name}")
        if row.text == f"{instrument_name}/{name}":
            findinst = True
    assert findinst

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

    # check for API instrument
    table = driver.wait_for_xpath('//*[contains(@class, "MuiList-root")]')
    findinst = False
    for row in table.find_elements_by_xpath(
        '//*[contains(@class, "MuiTypography-root")]'
    ):
        if row.text == f"{instrument_name2}/{name}":
            findinst = True
    assert findinst

    driver.refresh()

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

    # check for failure
    table = driver.wait_for_xpath('//*[contains(@class, "MuiTypography-root")]')
    finderror = False
    for row in table.find_elements_by_xpath(
        '//*[contains(@class, "MuiTypography-root")]'
    ):
        if row.text == "name: Instrument name matches another, please change.":
            finderror = True
    assert finderror
