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
        "text": reminder_text,
        "next_reminder": next_reminder.strftime("%Y-%m-%dT%H:%M:%S"),
        "reminder_delay": reminder_delay,
        "number_of_reminders": number_of_reminders,
    }

    status, data = api(
        "POST",
        endpoint,
        data=request_data,
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", endpoint, token=token)
    assert status == 200
    assert data["status"] == "success"
    data = data["data"]["reminders"]
    # find the index of reminder we just created using the text
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
        status, data = api(
            "GET",
            endpoint,
            token=token,
        )
        if data["status"] == "success":
            data = data["data"]["reminders"]
            # find the index of reminder we just created using the text
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


def test_reminder_on_source(super_admin_token):
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
    post_and_verify_reminder(endpoint, super_admin_token)


def test_reminder_on_shift(
    public_group,
    super_admin_token,
    super_admin_user,
):
    shift_name = str(uuid.uuid4())
    start_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    end_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
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

    endpoint = f"shift/{data['data']['id']}/reminders"
    post_and_verify_reminder(endpoint, super_admin_token)


def test_reminder_on_spectra(super_admin_token, lris):
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

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": obj_id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id = data["data"]["id"]

    endpoint = f"spectra/{spectrum_id}/reminders"
    post_and_verify_reminder(endpoint, super_admin_token)


def test_reminder_on_gcn(super_admin_token, gcn_GW190814):
    endpoint = f"gcn_event/{gcn_GW190814.id}/reminders"
    post_and_verify_reminder(endpoint, super_admin_token)
