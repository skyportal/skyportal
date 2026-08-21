import time
import uuid
from datetime import UTC, datetime, timedelta

from skyportal_py.reminders import ReminderPost
from skyportal_py.shifts import ShiftPost
from skyportal_py.sources import SourcePost
from skyportal_py.spectra import SpectrumPost

from skyportal.tests import client

from ....utils.naive_datetime import utcnow_naive


def post_and_verify_reminder(resource_type, resource_id, token):
    sp = client(token)
    reminder_text = str(uuid.uuid4())
    next_reminder = utcnow_naive() + timedelta(seconds=2)
    next_reminder = next_reminder.replace(microsecond=0)
    reminder_delay = 1
    number_of_reminders = 1

    sp.post_reminder(
        resource_id,
        ReminderPost(
            text=reminder_text,
            next_reminder=next_reminder.strftime("%Y-%m-%dT%H:%M:%S"),
            reminder_delay=reminder_delay,
            number_of_reminders=number_of_reminders,
        ),
        resource_type=resource_type,
    )

    reminders = sp.fetch_reminders(resource_id, resource_type=resource_type).reminders
    # find the index of reminder we just created using the text
    reminder_index = next(
        index
        for index, reminder in enumerate(reminders)
        if reminder.text == reminder_text
    )
    assert reminder_index != -1
    assert reminders[reminder_index].reminder_delay == reminder_delay
    assert reminders[reminder_index].number_of_reminders <= number_of_reminders
    assert reminders[reminder_index].next_reminder >= next_reminder

    n_retries = 0
    while n_retries < 5:
        reminders = sp.fetch_reminders(
            resource_id, resource_type=resource_type
        ).reminders
        # find the index of reminder we just created using the text
        reminder_index = next(
            index
            for index, reminder in enumerate(reminders)
            if reminder.text == reminder_text
        )
        if reminders[reminder_index].number_of_reminders < number_of_reminders:
            break
        time.sleep(2)
        n_retries += 1
    assert n_retries < 10
    assert len(reminders) == 1
    assert reminders[reminder_index].text == reminder_text
    assert reminders[reminder_index].reminder_delay == reminder_delay
    assert reminders[reminder_index].number_of_reminders == number_of_reminders - 1
    assert reminders[reminder_index].next_reminder > next_reminder
    return reminder_text


def test_reminder_on_source(super_admin_token):
    sp = client(super_admin_token)
    obj_id = str(uuid.uuid4())
    sp.post_source(
        SourcePost(
            id=obj_id,
            ra=24.6258,
            dec=-32.9024,
            redshift=3,
        )
    )

    source = sp.fetch_source(obj_id)

    post_and_verify_reminder("source", source.id, super_admin_token)


def test_reminder_on_shift(
    public_group,
    super_admin_token,
    super_admin_user,
):
    shift_name = str(uuid.uuid4())
    start_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    shift_id = (
        client(super_admin_token)
        .post_shift(
            ShiftPost(
                name=shift_name,
                group_id=public_group.id,
                start_date=start_date,
                end_date=end_date,
                description="Shift during GCN",
                shift_admins=[super_admin_user.id],
            )
        )
        .id
    )

    post_and_verify_reminder("shift", shift_id, super_admin_token)


def test_reminder_on_spectra(super_admin_token, lris):
    sp = client(super_admin_token)
    obj_id = str(uuid.uuid4())
    sp.post_source(
        SourcePost(
            id=obj_id,
            ra=24.6258,
            dec=-32.9024,
            redshift=3,
        )
    )

    sp.fetch_source(obj_id)

    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=obj_id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
        )
    ).id

    post_and_verify_reminder("spectra", spectrum_id, super_admin_token)


def test_reminder_on_gcn(super_admin_token, gcn_GW190814):
    post_and_verify_reminder("gcn_event", gcn_GW190814.id, super_admin_token)
