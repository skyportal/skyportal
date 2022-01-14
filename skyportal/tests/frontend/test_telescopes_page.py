from skyportal.tests import api

import uuid


def test_telescope_frontend(super_admin_token, super_admin_user, driver):

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/telescopes")

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

    # check for API instrument
    driver.wait_for_xpath(f'//span[text()="{name}"]')

    # add dropdown instrument
    name2 = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(name2)
    driver.wait_for_xpath('//*[@id="root_nickname"]').send_keys(name2)
    driver.wait_for_xpath('//*[@id="root_diameter"]').send_keys('2.0')

    tab = driver.find_element_by_xpath('//*[@class="MuiFormGroup-root"]')
    for row in tab.find_elements_by_xpath('//span[text()="Yes"]'):
        row.click()

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for dropdown instrument
    driver.wait_for_xpath(f'//span[text()="{name2}"]')
