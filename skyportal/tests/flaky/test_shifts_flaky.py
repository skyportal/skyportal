from skyportal.tests import api
from selenium.webdriver.common.keys import Keys
from datetime import date, timedelta
import uuid


def test_super_user_post_shift(
    public_group, super_admin_token, super_admin_user, driver
):

    driver.get(f"/become_user/{super_admin_user.id}")

    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    request_data = {
        'name': name,
        'group_id': public_group.id,
        'start_date': start_date,
        'end_date': end_date,
        'description': 'the Night Shift',
        'shift_admins': [super_admin_user.id],
    }

    status, data = api('POST', 'shifts', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    start_date = date.today().strftime("%m/%d/%Y")
    end_date = (date.today() + timedelta(days=1)).strftime("%m/%d/%Y")

    # go to the shift page
    driver.get("/shifts")

    # check for API shift
    driver.wait_for_xpath(f'//*[text()[contains(.,"{name}")]]', timeout=20)

    form_name = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(form_name)
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys(start_date)
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('P')

    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys(end_date)
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('P')

    driver.click_xpath('//*[@id="root_group_id"]')
    driver.click_xpath('//li[contains(text(), "Sitewide Group")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for dropdown shift
    event_shift_xpath = f'//*[text()[contains(.,"{form_name}")]]'
    driver.wait_for_xpath(event_shift_xpath)
    driver.click_xpath(event_shift_xpath)

    # check for leave shift button
    leave_button_xpath = '//*[@id="leave_button"]'
    driver.wait_for_xpath(leave_button_xpath)
    driver.click_xpath(leave_button_xpath)

    driver.wait_for_xpath_to_disappear(leave_button_xpath)

    # check for join shift button
    join_button_xpath = '//*[@id="join_button"]'
    driver.wait_for_xpath(join_button_xpath)
    driver.click_xpath(join_button_xpath)

    driver.wait_for_xpath_to_disappear(join_button_xpath)

    # check for delete shift button
    delete_button_xpath = '//*[@id="delete_button"]'
    driver.wait_for_xpath(delete_button_xpath)
    driver.click_xpath(delete_button_xpath)
    driver.wait_for_xpath_to_disappear(f'//*[text()[contains(.,"{form_name}")]]')

    assert (
        len(driver.find_elements_by_xpath(f'//*[text()[contains(.,"{form_name}")]]'))
        == 0
    )
