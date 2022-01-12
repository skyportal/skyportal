from skyportal.tests import api


def test_super_user_post_allocation(
    sedm, public_group, super_admin_token, super_admin_user, driver
):

    request_data = {
        'group_id': public_group.id,
        'instrument_id': sedm.id,
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

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/allocations")

    driver.wait_for_xpath('//*[@id="root_pi"]').send_keys('Shri')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01/01/2022')
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('02/01/2022')
    driver.wait_for_xpath('//*[@id="root_hours_allocated"]').send_keys('100')
    driver.click_xpath('//*[@id="root_instrument_id"]')
    driver.click_xpath('//li[contains(text(), "SEDM")]')
    driver.click_xpath('//*[@id="root_group_id"]')
    driver.click_xpath('//li[contains(text(), "Sitewide Group")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    driver.wait_for_xpath('//div[contains(text(), "SEDM")]')
