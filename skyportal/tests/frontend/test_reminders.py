import os
import uuid
import time

from skyportal.tests import api
from datetime import date, timedelta, datetime
from selenium.webdriver.common.keys import Keys
from skyportal.tests.api import post_and_verify_reminder


def post_and_verify_reminder_frontend(driver, reminder_text):
    search_button_xpath = driver.wait_for_xpath(
        '//button[@data-testid="Search-iconButton"]'
    )
    driver.scroll_to_element_and_click(search_button_xpath)
    search_bar = driver.wait_for_xpath('//input[@aria-label="Search"]')

    search_bar.send_keys(f"{reminder_text}")
    driver.wait_for_xpath(f'//*[text()="{reminder_text}"]', timeout=10)
    search_bar.clear()

    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//*[@data-testid="AddIcon"]')
    )
    reminder_text_2 = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_text"]').send_keys(reminder_text_2)
    next_reminder = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%YT%I:%M %p")
    driver.wait_for_xpath('//*[@id="root_next_reminder"]').send_keys(
        next_reminder[0:11]
    )
    driver.wait_for_xpath('//*[@id="root_next_reminder"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_next_reminder"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_next_reminder"]').send_keys('P')
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
    start_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
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

    post_and_verify_reminder_frontend(driver, reminder_text)


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

    post_and_verify_reminder_frontend(driver, reminder_text)


# frontend for the reminders on spectra is not implemented yet


def test_reminder_on_gcn(driver, super_admin_user, super_admin_token):
    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for event to load
    for n_times in range(26):
        status, data = api(
            'GET', "gcn_event/2019-08-14T21:10:39", token=super_admin_token
        )
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25
    gcn_event_id = data['data']['id']

    endpoint = f"gcn_event/{gcn_event_id}/reminders"
    reminder_text = post_and_verify_reminder(endpoint, super_admin_token)
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/gcn_events/2019-08-14T21:10:39")
    driver.wait_for_xpath('//*[contains(.,"190814 21:10:39")]', timeout=30)
    driver.click_xpath('//*[@data-testid="NotificationsOutlinedIcon"]')
    driver.wait_for_xpath('//*[@href="/gcn_events/2019-08-14T21:10:39"]')
    driver.click_xpath('//*[@data-testid="NotificationsOutlinedIcon"]')

    post_and_verify_reminder_frontend(driver, reminder_text)
