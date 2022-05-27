from skyportal.tests import api
from selenium.webdriver.common.keys import Keys
from datetime import date, timedelta
import uuid
from selenium.common.exceptions import TimeoutException
import time


def test_shift(
    public_group,
    super_admin_token,
    super_admin_user,
    user,
    view_only_user,
    shift_admin,
    shift_user,
    driver,
):
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

    driver.get(f"/become_user/{super_admin_user.id}")
    # go to the shift page
    driver.get(f"/shifts/{data['data']['id']}")

    # check for API shift
    try:
        driver.wait_for_xpath(
            f'//*/strong[contains(.,"{name}")]',
            timeout=10,
        )
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(
            f'//*/strong[contains(.,"{name}")]',
            timeout=10,
        )

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

    # check for shift in calendar and click it
    event_shift_xpath = f'//*/strong[contains(.,"{form_name}")]'
    driver.wait_for_xpath(event_shift_xpath)
    driver.click_xpath(event_shift_xpath)

    # check for deactivated button to add users
    deactivated_add_user_button = '//*[@id="deactivated-add-users-button"]'
    driver.wait_for_xpath(deactivated_add_user_button)

    # check for the dropdown to add a user
    select_users = '//*[@id="select-users--multiple-chip"]'
    driver.wait_for_xpath(select_users)
    driver.click_xpath(select_users)
    driver.wait_for_xpath(f'//li[@id="select_users"]/*[@id="{user.id}"]')
    driver.click_xpath(f'//li[@id="select_users"]/*[@id="{user.id}"]')

    # check for button to add users
    remove_users_button = '//*[@id="deactivated-remove-users-button"]'
    driver.wait_for_xpath(remove_users_button)
    add_users_button = '//*[@id="add-users-button"]'
    driver.wait_for_xpath(add_users_button)
    driver.click_xpath(add_users_button)

    # check if user has been added
    shift_members = '//*[@id="current_shift_members"]'
    driver.wait_for_xpath(shift_members + f'[contains(text(), "{user.username}")]')

    # check for the dropdown to add and remove users
    select_users = '//*[@id="select-users--multiple-chip"]'
    driver.wait_for_xpath(select_users)
    driver.click_xpath(select_users)
    driver.wait_for_xpath(f'//li[@id="select_users"]/*[@id="{user.id}"]')
    driver.click_xpath(f'//li[@id="select_users"]/*[@id="{user.id}"]')

    driver.wait_for_xpath(f'//li[@id="select_users"]/*[@id="{view_only_user.id}"]')
    driver.click_xpath(f'//li[@id="select_users"]/*[@id="{view_only_user.id}"]')

    # check for button to add and remove users
    add_users_button = '//*[@id="add-users-button"]'
    driver.wait_for_xpath(add_users_button)
    driver.click_xpath(add_users_button)

    remove_users_button = '//*[@id="remove-users-button"]'
    # As the component rerenders, the remove button will be deactivated for a bit, so we wait for the xpath to stay for a second to allow the button to be clickable
    # if we checked for the xpath right now, it might disappear right after when we try to click it. So we add a little delay before clicking the button
    time.sleep(1)
    driver.click_xpath(remove_users_button)

    # check if user has been added and other user has been removed
    shift_members = '//*[@id="current_shift_members"]'

    driver.wait_for_xpath_to_disappear(
        shift_members + f'[contains(text(), "{user.username}")]'
    )

    driver.wait_for_xpath(
        shift_members + f'[contains(text(), "{view_only_user.username}")]'
    )

    # check for the dropdown to remove users
    select_users = '//*[@id="select-users--multiple-chip"]'
    driver.wait_for_xpath(select_users)
    driver.click_xpath(select_users)

    driver.wait_for_xpath(f'//li[@id="select_users"]/*[@id="{view_only_user.id}"]')
    driver.click_xpath(f'//li[@id="select_users"]/*[@id="{view_only_user.id}"]')

    # check for button to remove users
    deactivated_add_users_button = '//*[@id="deactivated-add-users-button"]'
    driver.wait_for_xpath(deactivated_add_users_button)
    remove_users_button = '//*[@id="remove-users-button"]'
    driver.wait_for_xpath(remove_users_button)
    driver.click_xpath(remove_users_button)

    # check if user has been removed
    shift_members = '//*[@id="current_shift_members"]'

    driver.wait_for_xpath(
        shift_members + f'[not(contains(text(), "{view_only_user.username}"))]'
    )

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

    driver.get(f"/become_user/{shift_user.id}")

    driver.get("/shifts")

    shift_on_calendar = f'//*/span/strong[contains(.,"{form_name}")]'
    # check for API shift
    driver.wait_for_xpath(
        shift_on_calendar,
        timeout=30,
    )

    driver.click_xpath(shift_on_calendar)

    # check for join shift button
    join_button_xpath = '//*[@id="join_button"]'
    driver.wait_for_xpath(join_button_xpath)
    driver.click_xpath(join_button_xpath)

    driver.wait_for_xpath_to_disappear(join_button_xpath)

    # check if user has been added
    shift_members = '//*[@id="current_shift_members"]'
    driver.wait_for_xpath(
        shift_members + f'[contains(text(), "{shift_user.username}")]'
    )

    # check for button to ask for replacement
    ask_for_replacement_button_xpath = '//*[@id="ask-for-replacement-button"]'
    driver.wait_for_xpath(ask_for_replacement_button_xpath)
    driver.click_xpath(ask_for_replacement_button_xpath)

    driver.wait_for_xpath_to_disappear(ask_for_replacement_button_xpath)

    # change to another user
    driver.get(f"/become_user/{shift_admin.id}")

    driver.get("/")

    # look for the replacement request notification
    notification_bell = '//*[@data-testid="notificationsBadge"]'
    driver.wait_for_xpath(notification_bell)
    driver.click_xpath(notification_bell)

    notification_xpath = (
        f'//ul/a/p[contains(text(),"needs a replacement for shift: {form_name}")]'
    )
    driver.wait_for_xpath(notification_xpath)
    driver.click_xpath(notification_xpath, timeout=10)

    # check for API shift
    driver.wait_for_xpath(
        shift_on_calendar,
        timeout=30,
    )

    driver.click_xpath(shift_on_calendar)

    # check for the dropdown to choose who to replace

    # check for the dropdown to add a user
    select_users = '//*[@id="select-user-replace-chip"]'
    driver.wait_for_xpath(select_users)
    driver.click_xpath(select_users)
    driver.wait_for_xpath(
        f'//li[@id="select_user_to_replace"]/*[@id="{shift_user.id}"]'
    )
    driver.click_xpath(f'//li[@id="select_user_to_replace"]/*[@id="{shift_user.id}"]')

    # check for button to add and remove users
    replace_user_button = '//*[@id="replace-users-button"]'
    driver.wait_for_xpath(replace_user_button)
    driver.click_xpath(replace_user_button)

    driver.wait_for_xpath_to_disappear(replace_user_button)

    # check if user has been removed
    shift_members = '//*[@id="current_shift_members"]'
    driver.wait_for_xpath_to_disappear(
        shift_members + f'[contains(text(), "{shift_user.username}")]'
    )

    # check if user has been added
    shift_members = '//*[@id="current_shift_members"]'
    driver.wait_for_xpath(
        shift_members + f'[contains(text(), "{shift_admin.username}")]'
    )

    driver.get(f"/become_user/{super_admin_user.id}")
    # go to the shift page
    driver.get("/shifts")

    # check for API shift
    driver.wait_for_xpath(
        shift_on_calendar,
        timeout=30,
    )

    driver.click_xpath(shift_on_calendar)

    delete_button_xpath = '//*[@id="delete_button"]'
    driver.wait_for_xpath(delete_button_xpath)
    driver.click_xpath(delete_button_xpath)
    driver.wait_for_xpath_to_disappear(
        f'//*[@id="current_shift_title"][contains(.,"{form_name}")]'
    )
    driver.wait_for_xpath_to_disappear(f'//*/strong[contains(.,"{form_name}")]')

    assert (
        len(
            driver.find_elements_by_xpath(
                f'//*[@id="current_shift_title"][contains(.,"{form_name}")]'
            )
        )
        == 0
    )

    assert (
        len(driver.find_elements_by_xpath(f'//*/strong[contains(.,"{form_name}")]'))
        == 0
    )
