import time
import uuid
from datetime import UTC, datetime, timedelta

from playwright.sync_api import expect

from skyportal.tests import api

from ...utils.naive_datetime import utcnow_naive


def post_and_verify_reminder(endpoint, token):
    reminder_text = str(uuid.uuid4())
    next_reminder = utcnow_naive() + timedelta(seconds=2)
    next_reminder = next_reminder.replace(microsecond=0)
    reminder_delay = 1
    number_of_reminders = 1
    request_data = {
        "text": reminder_text,
        "next_reminder": next_reminder.strftime("%Y-%m-%dT%H:%M:%S"),
        "reminder_delay": reminder_delay,
        "number_of_reminders": number_of_reminders,
    }

    status, data = api("POST", endpoint, data=request_data, token=token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", endpoint, token=token)
    assert status == 200
    assert data["status"] == "success"
    data = data["data"]["reminders"]
    reminder_index = next(
        index
        for index, reminder in enumerate(data)
        if reminder["text"] == reminder_text
    )
    assert reminder_index != -1
    assert data[reminder_index]["reminder_delay"] == reminder_delay
    assert data[reminder_index]["number_of_reminders"] <= number_of_reminders
    assert (
        datetime.strptime(data[reminder_index]["next_reminder"], "%Y-%m-%dT%H:%M:%S")
        >= next_reminder
    )

    n_retries = 0
    while n_retries < 5:
        status, data = api("GET", endpoint, token=token)
        if data["status"] == "success":
            data = data["data"]["reminders"]
            reminder_index = next(
                index
                for index, reminder in enumerate(data)
                if reminder["text"] == reminder_text
            )
            if data[reminder_index]["number_of_reminders"] < number_of_reminders:
                break
        time.sleep(2)
        n_retries += 1
    assert n_retries < 10
    assert status == 200
    assert len(data) == 1
    assert data[reminder_index]["text"] == reminder_text
    assert data[reminder_index]["reminder_delay"] == reminder_delay
    assert data[reminder_index]["number_of_reminders"] == number_of_reminders - 1
    assert (
        datetime.strptime(data[reminder_index]["next_reminder"], "%Y-%m-%dT%H:%M:%S")
        > next_reminder
    )
    return reminder_text


def post_and_verify_reminder_frontend(page, reminder_text, resource_id):
    # The reminders data grid exposes a quick-filter search input that filters
    # rows as you type.
    search = page.locator('//*[@data-testid="reminders-quick-filter"]//input').first
    search.fill(reminder_text)
    expect(page.locator(f'//*[text()="{reminder_text}"]').first).to_be_visible()
    search.fill("")

    page.locator(f'//button[@name="new_reminder_{resource_id}"]').first.click()

    reminder_text_2 = str(uuid.uuid4())

    expect(page.locator('//*[contains(.,"New Reminder on ")]').first).to_be_visible()
    # let the form load with default values before typing
    time.sleep(2)

    text_input = page.locator('//*[@id="root_text"]').first
    text_input.click()
    text_input.fill(reminder_text_2)

    page.locator('//form[@id="reminder-form"]/*/*[@type="submit"]').first.click()
    expect(page.locator('//*[contains(.,"New Reminder on ")]').first).to_be_hidden()

    search = page.locator('//*[@data-testid="reminders-quick-filter"]//input').first
    search.fill(reminder_text_2)
    expect(page.locator(f'//*[text()="{reminder_text_2}"]').first).to_be_visible()
    search.fill("")


def test_reminder_on_shift(page, public_group, super_admin_user, super_admin_token):
    shift_name = str(uuid.uuid4())
    start_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    request_data = {
        "name": shift_name,
        "group_id": public_group.id,
        "start_date": start_date,
        "end_date": end_date,
        "description": "Shift during GCN",
        "shift_admins": [super_admin_user.id],
    }

    status, data = api("POST", "shifts", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    shift_id = data["data"]["id"]
    endpoint = f"shift/{shift_id}/reminders"
    reminder_text = post_and_verify_reminder(endpoint, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/shifts/{shift_id}")
    # One event can render on multiple days; click the visible one.
    page.locator(
        f'//*[@data-testid="event_shift_name" and contains(text(), "{shift_name}")]/..'
    ).locator("visible=true").first.click()

    page.locator('//*[@data-testid="NotificationsOutlinedIcon"]').first.click()
    expect(page.locator(f'//*[@href="/shifts/{shift_id}"]').first).to_be_visible()
    page.keyboard.press("Escape")

    post_and_verify_reminder_frontend(page, reminder_text, shift_id)


def test_reminder_on_source(page, super_admin_user, super_admin_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": 24.6258, "dec": -32.9024, "redshift": 3},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"sources/{obj_id}", token=super_admin_token)
    assert status == 200

    endpoint = f"source/{data['data']['id']}/reminders"
    reminder_text = post_and_verify_reminder(endpoint, super_admin_token)
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{obj_id}")
    expect(page.locator(f'//*[contains(.,"{obj_id}")]').first).to_be_visible(
        timeout=30000
    )
    page.locator('//*[@data-testid="NotificationsOutlinedIcon"]').first.click()
    expect(page.locator(f'//*[@href="/source/{obj_id}"]').first).to_be_visible()
    page.keyboard.press("Escape")

    post_and_verify_reminder_frontend(page, reminder_text, obj_id)
