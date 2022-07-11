from skyportal.tests import api
from datetime import date, timedelta
import uuid
import time


def test_shift_reminder(
    public_group,
    super_admin_token,
    super_admin_user,
):
    # add a shift to the group, with a start day one day before today,
    # and an end day one day after today
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

    reminder_text = str(uuid.uuid4())
    next_reminder = date.today() + timedelta(seconds=10)
    reminder_delay = 1
    number_of_reminders = 2
    request_data = {
        'text': reminder_text,
        'next_reminder': next_reminder.strftime("%Y-%m-%dT%H:%M:%S"),
        'reminder_delay': reminder_delay,
        'number_of_reminders': number_of_reminders,
    }
    status, data = api(
        'POST',
        f'shift/{shift_id}/reminders',
        data=request_data,
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'shift/{shift_id}/reminders', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    data = data['data']
    assert len(data) == 1
    assert data[0]['text'] == reminder_text
    assert data[0]['next_reminder'] == next_reminder.strftime("%Y-%m-%dT%H:%M:%S")
    assert data[0]['reminder_delay'] == reminder_delay
    assert data[0]['number_of_reminders'] == number_of_reminders

    time.sleep(10)  # wait for the reminder to be sent
    status, data = api('GET', f'shift/{shift_id}/reminders', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    data = data['data']
    assert len(data) == 1
    assert data[0]['text'] == reminder_text
    assert data[0]['next_reminder'] == (
        next_reminder + timedelta(days=reminder_delay)
    ).strftime("%Y-%m-%dT%H:%M:%S")
    assert data[0]['reminder_delay'] == reminder_delay
    assert data[0]['number_of_reminders'] == number_of_reminders - 1
