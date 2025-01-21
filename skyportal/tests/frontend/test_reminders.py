import time
import uuid
from datetime import datetime, timedelta, timezone

from skyportal.tests import api


def post_and_verify_reminder(endpoint, token):
    reminder_text = str(uuid.uuid4())
    next_reminder = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        seconds=2
    )
    next_reminder = next_reminder.replace(microsecond=0)
    reminder_delay = 1
    number_of_reminders = 1
    request_data = {
        'text': reminder_text,
        'next_reminder': next_reminder.strftime("%Y-%m-%dT%H:%M:%S"),
        'reminder_delay': reminder_delay,
        'number_of_reminders': number_of_reminders,
    }

    status, data = api(
        'POST',
        endpoint,
        data=request_data,
        token=token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', endpoint, token=token)
    assert status == 200
    assert data['status'] == 'success'
    data = data['data']['reminders']
    # find the index of reminder we just created using the text
    reminder_index = next(
        index
        for index, reminder in enumerate(data)
        if reminder['text'] == reminder_text
    )
    assert reminder_index != -1
    assert data[reminder_index]['reminder_delay'] == reminder_delay
    assert data[reminder_index]['number_of_reminders'] <= number_of_reminders
    assert (
        datetime.strptime(data[reminder_index]['next_reminder'], "%Y-%m-%dT%H:%M:%S")
        >= next_reminder
    )

    n_retries = 0
    while n_retries < 30:
        status, data = api(
            'GET',
            endpoint,
            token=token,
        )
        if data['status'] == 'success':
            data = data['data']['reminders']
            # find the index of reminder we just created using the text
            reminder_index = next(
                index
                for index, reminder in enumerate(data)
                if reminder['text'] == reminder_text
            )
            if data[reminder_index]['number_of_reminders'] < number_of_reminders:
                break
        time.sleep(2)
        n_retries += 1
    assert n_retries < 10
    assert status == 200
    assert len(data) == 1
    assert data[reminder_index]['text'] == reminder_text
    assert data[reminder_index]['reminder_delay'] == reminder_delay
    assert data[reminder_index]['number_of_reminders'] == number_of_reminders - 1
    assert (
        datetime.strptime(data[reminder_index]['next_reminder'], "%Y-%m-%dT%H:%M:%S")
        > next_reminder
    )
    return reminder_text


def post_and_verify_reminder_frontend(driver, reminder_text, resource_id):
    search_button_xpath = driver.wait_for_xpath(
        '//*[@data-testid="Reminders"]//button[@aria-label="Search"]'
    )
    driver.scroll_to_element_and_click(search_button_xpath)
    search_bar = driver.wait_for_xpath('//input[@aria-label="Search"]')

    search_bar.send_keys(f"{reminder_text}")
    driver.wait_for_xpath(f'//*[text()="{reminder_text}"]', timeout=10)
    search_bar.clear()

    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(f'//button[@name="new_reminder_{resource_id}"]')
    )

    # timeout to let the form load with default values
    time.sleep(2)

    reminder_text_2 = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_text"]').send_keys(reminder_text_2)

    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//form[@id="reminder-form"]/*/*[@type="submit"]')
    )
    driver.wait_for_xpath_to_disappear('//*[contains(.,"New Reminder on ")]')
    search_bar = driver.wait_for_xpath('//input[@aria-label="Search"]')
    search_bar.send_keys(f"{reminder_text_2}")
    driver.wait_for_xpath(f'//*[text()="{reminder_text_2}"]', timeout=10)
    search_bar.clear()


def test_reminder_on_shift(
    driver,
    public_group,
    super_admin_user,
    super_admin_token,
):
    shift_name = str(uuid.uuid4())
    start_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    end_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    request_data = {
        'name': shift_name,
        'group_id': public_group.id,
        'start_date': start_date,
        'end_date': end_date,
        'description': 'Shift during GCN',
        'shift_admins': [super_admin_user.id],
    }

    status, data = api('POST', 'shifts', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    shift_id = data['data']['id']
    endpoint = f"shift/{shift_id}/reminders"
    reminder_text = post_and_verify_reminder(endpoint, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/shifts/{shift_id}")
    driver.wait_for_xpath(
        f'//*/strong[contains(.,"{shift_name}")]',
        timeout=30,
    )
    driver.click_xpath('//*[@data-testid="NotificationsOutlinedIcon"]')
    driver.wait_for_xpath(f'//*[@href="/shifts/{shift_id}"]')
    driver.click_xpath('//*[@data-testid="NotificationsOutlinedIcon"]')

    post_and_verify_reminder_frontend(driver, reminder_text, shift_id)


def test_reminder_on_source(driver, super_admin_user, super_admin_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 24.6258,
            "dec": -32.9024,
            "redshift": 3,
        },
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"sources/{obj_id}", token=super_admin_token)
    assert status == 200

    endpoint = f"source/{data['data']['id']}/reminders"
    reminder_text = post_and_verify_reminder(endpoint, super_admin_token)
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{obj_id}")
    driver.wait_for_xpath(
        f'//*[contains(.,"{obj_id}")]',
        timeout=30,
    )
    driver.click_xpath('//*[@data-testid="NotificationsOutlinedIcon"]')
    driver.wait_for_xpath(f'//*[@href="/source/{obj_id}"]')
    driver.click_xpath('//*[@data-testid="NotificationsOutlinedIcon"]')

    post_and_verify_reminder_frontend(driver, reminder_text, obj_id)


# frontend for the reminders on spectra is not implemented yet
